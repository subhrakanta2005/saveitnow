from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import Response
from urllib.parse import quote
import yt_dlp
import httpx
import re
import os


app = FastAPI(title="SaveItNow API")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://saveitnow.vercel.app").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

RAPIDAPI_KEY    = os.getenv("RAPIDAPI_KEY", "")
INSTAGRAM_HOST  = "instagram120.p.rapidapi.com"
YOUTUBE_HOST    = "youtube138.p.rapidapi.com"
FACEBOOK_HOST   = "facebook-media-downloader1.p.rapidapi.com"

RAPIDAPI_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "Content-Type": "application/json",
}

class URLRequest(BaseModel):
    url: str

def detect_platform(url: str) -> str:
    patterns = {
        "instagram": r"instagram\.com",
        "youtube":   r"(youtube\.com|youtu\.be)",
        "facebook":  r"(facebook\.com|fb\.watch)",
        "tiktok":    r"tiktok\.com",
        "twitter":   r"(twitter\.com|x\.com)",
        "reddit":    r"reddit\.com",
        "pinterest": r"pinterest\.com",
    }
    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "other"

def format_size(b):
    if not b: return None
    if b > 1048576: return f"{b/1048576:.1f} MB"
    return f"{b/1024:.0f} KB"

# ══════════════════════════════════════════
# INSTAGRAM — instagram120
# Endpoint used: POST /links
# Response shape: a JSON array of items, each with
#   "urls": [{ "url", "extension", "quality", ... }],
#   "meta": { "title", "username", ... },
#   "pictureUrl"
# ══════════════════════════════════════════
async def instagram_info(url: str) -> dict:
    if not RAPIDAPI_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: RAPIDAPI_KEY is not set.")

    headers = {**RAPIDAPI_HEADERS, "x-rapidapi-host": INSTAGRAM_HOST}

    async with httpx.AsyncClient(timeout=25) as client:
        try:
            r = await client.post(
                f"https://{INSTAGRAM_HOST}/api/instagram/links",
                headers=headers,
                json={"url": url},
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not reach Instagram API: {e}")

        if r.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Could not fetch Instagram media (status {r.status_code}): {r.text[:300]}"
            )

        try:
            data = r.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Instagram API returned an invalid response.")

    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=400, detail="Could not fetch Instagram media. Make sure the content is public.")

    formats = []
    seen = set()
    for idx, entry in enumerate(data, start=1):
        for u in (entry.get("urls") or []):
            video_url = u.get("url")
            if not video_url or video_url in seen:
                continue
            seen.add(video_url)
            ext = u.get("extension", "mp4")
            quality = u.get("quality")
            kind = "Video" if ext == "mp4" else "Image"
            label = f"Item {idx} – {kind} {quality}p" if quality else f"Item {idx} – {kind}"
            formats.append({
                "format_id": video_url,
                "label": label,
                "ext": ext,
                "filesize": None,
                "direct_url": video_url,
            })

    if not formats:
        raise HTTPException(status_code=400, detail="Could not fetch Instagram media. Make sure the content is public.")

    # Prefer videos first, keep relative order otherwise
    formats.sort(key=lambda f: f["ext"] != "mp4")

    first = data[0]
    meta = first.get("meta", {}) or {}

    return {
        "title": meta.get("title") or "Instagram Media",
        "thumbnail": (
            f"{BACKEND_PUBLIC_URL}/proxy/image?url={quote(first.get('pictureUrl'), safe='')}"
            if first.get("pictureUrl") else None
        ),
        "duration": None,
        "platform": "instagram",
        "uploader": meta.get("username"),
        "formats": formats,
    }

# ══════════════════════════════════════════
# YOUTUBE — youtube138
# Endpoints: GET /search, GET /videos/info
# POST /download — gets stream URL
# ══════════════════════════════════════════
async def youtube_info(url: str) -> dict:
    headers = {**RAPIDAPI_HEADERS, "x-rapidapi-host": YOUTUBE_HOST}

    # Extract video ID
    vid_id = None
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    if match:
        vid_id = match.group(1)

    if not vid_id:
        raise HTTPException(status_code=400, detail="Could not extract YouTube video ID from URL.")

    async with httpx.AsyncClient(timeout=25) as client:
        try:
            r = await client.get(
                f"https://{YOUTUBE_HOST}/videos/info",
                headers=headers,
                params={"id": vid_id},
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            # Fallback to yt-dlp if RapidAPI fails
            return await ytdlp_info(url, "youtube")

    # Parse youtube138 response
    video_details = data.get("videoDetails") or data.get("video") or {}
    streaming = data.get("streamingData") or {}

    formats = []
    # Try adaptive formats first (separate video streams)
    adaptive = streaming.get("adaptiveFormats") or []
    for f in adaptive:
        if "video" in f.get("mimeType", "") and "mp4" in f.get("mimeType", ""):
            height = f.get("height")
            if height:
                formats.append({
                    "format_id": f.get("itag", str(height)),
                    "label": f"{height}p",
                    "ext": "mp4",
                    "filesize": format_size(f.get("contentLength")),
                    "direct_url": f.get("url"),
                })

    # Progressive formats (video+audio combined)
    for f in (streaming.get("formats") or []):
        if "mp4" in f.get("mimeType", ""):
            height = f.get("height")
            if height:
                formats.append({
                    "format_id": f.get("itag", str(height)),
                    "label": f"{height}p (HD)",
                    "ext": "mp4",
                    "filesize": format_size(f.get("contentLength")),
                    "direct_url": f.get("url"),
                })

    # Sort by quality
    formats.sort(key=lambda x: int(x["label"].split("p")[0]) if x["label"][0].isdigit() else 0, reverse=True)
    formats = formats[:5]  # top 5 qualities

    # Audio only
    for f in adaptive:
        if "audio" in f.get("mimeType", ""):
            formats.append({
                "format_id": "audio",
                "label": "Audio Only (MP3)",
                "ext": "mp3",
                "filesize": format_size(f.get("contentLength")),
                "direct_url": f.get("url"),
            })
            break

    if not formats:
        # Fallback to yt-dlp
        return await ytdlp_info(url, "youtube")

    title = video_details.get("title") or data.get("title") or "YouTube Video"
    thumbnail = None
    thumbs = video_details.get("thumbnail", {}).get("thumbnails") or []
    if thumbs:
        thumbnail = thumbs[-1].get("url")

    return {
        "title": title,
        "thumbnail": thumbnail,
        "duration": video_details.get("lengthSeconds"),
        "platform": "youtube",
        "uploader": video_details.get("author") or video_details.get("channelTitle"),
        "formats": formats,
    }

# ══════════════════════════════════════════
# FACEBOOK — facebook-media-downloader1
# POST /get_media  body: { "url": "..." }
# ══════════════════════════════════════════
async def facebook_info(url: str) -> dict:
    headers = {**RAPIDAPI_HEADERS, "x-rapidapi-host": FACEBOOK_HOST}
    async with httpx.AsyncClient(timeout=25) as client:
        try:
            r = await client.post(
                f"https://{FACEBOOK_HOST}/get_media",
                headers=headers,
                json={"url": url},
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            # Fallback to yt-dlp
            return await ytdlp_info(url, "facebook")

    direct = data.get("direct_media_url") or data.get("url")
    if not direct:
        return await ytdlp_info(url, "facebook")

    media_type = data.get("media_type", "video")
    formats = [{
        "format_id": direct,
        "label": f"{media_type.capitalize()}",
        "ext": "mp4",
        "filesize": None,
        "direct_url": direct,
    }]

    # HD version if available
    hd_url = data.get("hd_url") or data.get("hd")
    if hd_url and hd_url != direct:
        formats.insert(0, {
            "format_id": hd_url,
            "label": "HD Video",
            "ext": "mp4",
            "filesize": None,
            "direct_url": hd_url,
        })

    return {
        "title": data.get("title") or "Facebook Video",
        "thumbnail": data.get("thumbnail"),
        "duration": data.get("duration"),
        "platform": "facebook",
        "uploader": data.get("page_name") or data.get("author"),
        "formats": formats,
    }

# ══════════════════════════════════════════
# YT-DLP — TikTok, Twitter, Reddit,
#           Pinterest, and everything else
# ══════════════════════════════════════════
async def ytdlp_info(url: str, platform: str = "other") -> dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()
        if "private" in msg or "login" in msg:
            raise HTTPException(status_code=400, detail="This content is private or requires login.")
        raise HTTPException(status_code=400, detail="Could not fetch this URL. Make sure it is public.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    formats = []
    seen = set()
    for f in (info.get("formats") or []):
        if f.get("vcodec") != "none" and f.get("height") and f.get("url"):
            label = f"{f['height']}p"
            if label not in seen:
                seen.add(label)
                formats.append({
                    "format_id": f["format_id"],
                    "label": label,
                    "ext": f.get("ext", "mp4"),
                    "filesize": format_size(f.get("filesize")),
                    "direct_url": f.get("url"),
                })

    formats.sort(key=lambda x: int(x["label"].replace("p", "")) if x["label"].endswith("p") else 0, reverse=True)
    formats = formats[:5]

    # Audio
    for f in (info.get("formats") or []):
        if f.get("vcodec") == "none" and f.get("acodec") != "none" and f.get("url"):
            formats.append({
                "format_id": f["format_id"],
                "label": "Audio Only (MP3)",
                "ext": "mp3",
                "filesize": format_size(f.get("filesize")),
                "direct_url": f.get("url"),
            })
            break

    if not formats and info.get("url"):
        formats.append({
            "format_id": "best",
            "label": "Best Quality",
            "ext": "mp4",
            "filesize": None,
            "direct_url": info.get("url"),
        })

    return {
        "title": info.get("title", "Video"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "platform": platform,
        "uploader": info.get("uploader") or info.get("channel"),
        "formats": formats,
    }

# ══════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════
@app.get("/")
def root():
    return {"status": "SaveItNow API running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://saveitnow.onrender.com")

@app.get("/proxy/image")
async def proxy_image(url: str):
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Referer": "https://www.instagram.com/",
            })
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail="Could not fetch image")
        content_type = r.headers.get("content-type", "image/jpeg")
        return Response(content=r.content, media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/info")
async def get_info(request: URLRequest):
    url = request.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL.")
    platform = detect_platform(url)
    try:
        if platform == "instagram":
            return await instagram_info(url)
        elif platform == "youtube":
            return await youtube_info(url)
        elif platform == "facebook":
            return await facebook_info(url)
        else:
            return await ytdlp_info(url, platform)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
async def download(request: URLRequest, format_id: str = "best"):
    platform = detect_platform(request.url)

    # RapidAPI platforms — format_id IS the direct URL
    if platform in ("instagram", "facebook", "youtube") and format_id.startswith("http"):
        return {"download_url": format_id, "title": "media", "ext": "mp4"}

    # yt-dlp platforms
    ydl_opts = {"quiet": True, "format": format_id, "skip_download": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
        direct_url = info.get("url")
        if not direct_url:
            for f in reversed(info.get("formats", [])):
                if f.get("url") and f.get("vcodec") != "none":
                    direct_url = f["url"]
                    break
        if not direct_url:
            raise HTTPException(status_code=404, detail="No downloadable URL found")
        return {"download_url": direct_url, "title": info.get("title", "video"), "ext": "mp4"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
