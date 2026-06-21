from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import httpx
import re
import os

app = FastAPI(title="SaveItNow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY_HERE")
INSTAGRAM_HOST = "instagram120.p.rapidapi.com"
FACEBOOK_HOST  = "facebook-media-downloader1.p.rapidapi.com"

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

@app.get("/")
def root():
    return {"status": "SaveItNow API running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ══════════════════════════════════════════
# INSTAGRAM — instagram120
# ══════════════════════════════════════════
async def instagram_info(url: str) -> dict:
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": INSTAGRAM_HOST,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"https://{INSTAGRAM_HOST}/links",
            headers=headers,
            json={"url": url},
        )
        r.raise_for_status()
        data = r.json()

    formats = []
    items = data.get("items") or data.get("data") or []
    for item in items:
        video_url = item.get("video_url") or item.get("url")
        if video_url:
            formats.append({
                "format_id": video_url,
                "label": item.get("resolution") or "Video",
                "ext": "mp4",
                "filesize": item.get("size"),
                "direct_url": video_url,
            })

    if not formats:
        async with httpx.AsyncClient(timeout=20) as client:
            r2 = await client.get(
                f"https://{INSTAGRAM_HOST}/get",
                headers=headers,
                params={"url": url},
            )
            d2 = r2.json()
            video_url = d2.get("video_url") or d2.get("url")
            if video_url:
                formats.append({
                    "format_id": video_url,
                    "label": "Video",
                    "ext": "mp4",
                    "filesize": None,
                    "direct_url": video_url,
                })

    return {
        "title": data.get("caption") or data.get("title") or "Instagram Media",
        "thumbnail": data.get("thumbnail") or data.get("display_url"),
        "duration": data.get("duration"),
        "platform": "instagram",
        "formats": formats,
    }

# ══════════════════════════════════════════
# FACEBOOK — facebook-media-downloader1
# POST /get_media  body: { "url": "..." }
# ══════════════════════════════════════════
async def facebook_info(url: str) -> dict:
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": FACEBOOK_HOST,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"https://{FACEBOOK_HOST}/get_media",
            headers=headers,
            json={"url": url},
        )
        r.raise_for_status()
        data = r.json()

    # Response fields: direct_media_url, media_type, source_url, status, thumbnail
    direct = data.get("direct_media_url")
    if not direct:
        raise HTTPException(status_code=400, detail="Facebook API returned no download URL")

    media_type = data.get("media_type", "video").capitalize()
    formats = [{
        "format_id": direct,
        "label": media_type,
        "ext": "mp4",
        "filesize": None,
        "direct_url": direct,
    }]

    return {
        "title": f"Facebook {media_type}",
        "thumbnail": data.get("thumbnail"),
        "duration": None,
        "platform": "facebook",
        "formats": formats,
    }

# ══════════════════════════════════════════
# YT-DLP — YouTube, TikTok, Twitter, Reddit,
#           Pinterest, and everything else
# ══════════════════════════════════════════
async def ytdlp_info(url: str, platform: str = "other") -> dict:
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []
    seen = set()
    for f in (info.get("formats") or []):
        if f.get("vcodec") != "none" and f.get("height"):
            label = f"{f['height']}p"
            if label not in seen:
                seen.add(label)
                formats.append({
                    "format_id": f["format_id"],
                    "label": label,
                    "ext": f.get("ext", "mp4"),
                    "filesize": f.get("filesize"),
                    "direct_url": f.get("url"),
                })
    formats.append({
        "format_id": "bestaudio/best",
        "label": "Audio Only (MP3)",
        "ext": "mp3",
        "filesize": None,
        "direct_url": None,
    })
    formats.sort(
        key=lambda x: int(x["label"].replace("p","")) if x["label"].endswith("p") else -1,
        reverse=True
    )

    return {
        "title": info.get("title", "Unknown"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "platform": platform,
        "formats": formats[:7],
    }

# ══════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════
@app.post("/info")
async def get_info(request: URLRequest):
    url = request.url
    platform = detect_platform(url)
    try:
        if platform == "instagram":
            return await instagram_info(url)
        elif platform == "facebook":
            return await facebook_info(url)
        else:
            # YouTube, TikTok, Twitter, Reddit, Pinterest, other → yt-dlp
            return await ytdlp_info(url, platform)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
async def download(request: URLRequest, format_id: str = "best"):
    platform = detect_platform(request.url)

    # RapidAPI platforms — format_id is the direct URL itself
    if platform in ("instagram", "facebook") and format_id.startswith("http"):
        return {"download_url": format_id, "title": "media", "ext": "mp4"}

    # yt-dlp platforms
    ydl_opts = {"quiet": True, "format": format_id, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
        direct_url = None
        if "url" in info:
            direct_url = info["url"]
        elif "formats" in info:
            for f in reversed(info["formats"]):
                if f.get("url") and f.get("vcodec") != "none":
                    direct_url = f["url"]
                    break
        if not direct_url:
            raise HTTPException(status_code=404, detail="No downloadable URL found")
        return {"download_url": direct_url, "title": info.get("title", "video"), "ext": "mp4"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
