from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import Response
from urllib.parse import quote, urlparse, urljoin
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import yt_dlp
import httpx
import re
import os
import socket
import ipaddress
import asyncio


app = FastAPI(title="SaveItNow API")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
    # Host suffixes, matched against the actual hostname only (not the
    # whole URL), so e.g. "netflix.com" can never match "x.com" just
    # because it happens to contain that substring.
    patterns = {
        "instagram": (r"instagram\.com$",),
        "youtube":   (r"youtube\.com$", r"youtu\.be$"),
        "facebook":  (r"facebook\.com$", r"fb\.watch$"),
        "tiktok":    (r"tiktok\.com$",),
        "twitter":   (r"twitter\.com$", r"(^|\.)x\.com$"),
        "reddit":    (r"reddit\.com$", r"redd\.it$"),
        "pinterest": (r"pinterest\.com$", r"pin\.it$"),
    }
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        host = ""
    if not host:
        return "other"
    for platform, host_patterns in patterns.items():
        for pattern in host_patterns:
            if re.search(pattern, host):
                return platform
    return "other"

def format_size(b):
    if not b: return None
    if b > 1048576: return f"{b/1048576:.1f} MB"
    return f"{b/1024:.0f} KB"

# Hosts our proxy endpoints are allowed to fetch from. Anything outside
# this list is rejected — otherwise /proxy/image and /proxy/download
# would be an open SSRF proxy that fetches any URL a caller supplies.
ALLOWED_PROXY_HOST_SUFFIXES = (
    "cdninstagram.com", "fbcdn.net", "fbsbx.com",
    "googlevideo.com", "ytimg.com",
    "redd.it", "redditmedia.com",
    "pinimg.com",
    "tiktokcdn.com", "tiktokcdn-us.com",
    "twimg.com",
)

def is_allowed_proxy_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return any(host == s or host.endswith("." + s) for s in ALLOWED_PROXY_HOST_SUFFIXES)

MAX_PROXY_REDIRECTS = 5

async def fetch_allowed_url(url: str, *, stream: bool, timeout: float, headers: dict):
    """
    Fetches `url` for the /proxy/* endpoints, re-checking the allowlist
    on every redirect hop. httpx's built-in follow_redirects=True only
    validates the URL you pass in — an allowed host that 302s elsewhere
    would otherwise let a caller pivot to an arbitrary destination.
    Caller is responsible for closing the returned client/response.
    """
    current_url = url
    client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)
    for _ in range(MAX_PROXY_REDIRECTS + 1):
        if not is_allowed_proxy_url(current_url):
            await client.aclose()
            raise HTTPException(status_code=400, detail="This host is not allowed to be proxied.")
        try:
            req = client.build_request("GET", current_url, headers=headers)
            resp = await client.send(req, stream=stream)
        except Exception:
            await client.aclose()
            raise HTTPException(status_code=400, detail="Could not reach the media host.")
        if resp.status_code in (301, 302, 303, 307, 308) and "location" in resp.headers:
            next_url = urljoin(current_url, resp.headers["location"])
            await resp.aclose()
            current_url = next_url
            continue
        return client, resp
    await client.aclose()
    raise HTTPException(status_code=400, detail="Too many redirects.")

async def is_public_http_url(url: str) -> bool:
    """
    Best-effort SSRF guard for URLs handed to yt-dlp's generic
    extractor (used for every platform we don't have a dedicated
    RapidAPI integration for). Rejects localhost/private/link-local/
    reserved addresses so the backend can't be used to probe internal
    services or cloud metadata endpoints (e.g. 169.254.169.254).
    This checks the URL yt-dlp is initially given — it can't fully
    account for redirects yt-dlp itself follows during extraction,
    but it blocks the straightforward SSRF attempts.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return True

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
        except Exception:
            raise HTTPException(status_code=400, detail="Could not reach Instagram API.")

        if r.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Could not fetch Instagram media. Make sure the content is public."
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
            direct_url = f.get("url")
            if height and direct_url:
                formats.append({
                    # format_id is the direct CDN URL itself (same
                    # convention as Instagram/Facebook) so the frontend
                    # can download it directly instead of re-resolving
                    # via yt-dlp against a bare itag number.
                    "format_id": direct_url,
                    "label": f"{height}p",
                    "ext": "mp4",
                    "filesize": format_size(f.get("contentLength")),
                    "direct_url": direct_url,
                })

    # Progressive formats (video+audio combined)
    for f in (streaming.get("formats") or []):
        if "mp4" in f.get("mimeType", ""):
            height = f.get("height")
            direct_url = f.get("url")
            if height and direct_url:
                formats.append({
                    "format_id": direct_url,
                    "label": f"{height}p (HD)",
                    "ext": "mp4",
                    "filesize": format_size(f.get("contentLength")),
                    "direct_url": direct_url,
                })

    # Sort by quality
    formats.sort(key=lambda x: int(x["label"].split("p")[0]) if x["label"][0].isdigit() else 0, reverse=True)
    formats = formats[:5]  # top 5 qualities

    # Audio only
    for f in adaptive:
        if "audio" in f.get("mimeType", "") and f.get("url"):
            formats.append({
                "format_id": f.get("url"),
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
    if not await is_public_http_url(url):
        raise HTTPException(status_code=400, detail="This URL cannot be processed.")

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
    except Exception:
        raise HTTPException(status_code=400, detail="Could not fetch this URL. Make sure it is public.")

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
@limiter.limit("60/minute")
async def proxy_image(request: Request, url: str):
    if not is_allowed_proxy_url(url):
        raise HTTPException(status_code=400, detail="This host is not allowed to be proxied.")
    client, r = await fetch_allowed_url(url, stream=False, timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Referer": "https://www.instagram.com/",
    })
    try:
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail="Could not fetch image")
        content_type = r.headers.get("content-type", "image/jpeg")
        return Response(content=r.content, media_type=content_type)
    finally:
        await r.aclose()
        await client.aclose()

@app.get("/proxy/download")
@limiter.limit("30/minute")
async def proxy_download(request: Request, url: str, filename: str = "media", ext: str = "mp4"):
    """
    Streams a direct CDN media URL back through our own origin with a
    Content-Disposition header, so the browser actually saves the file
    with the right name. This is required because the `download`
    attribute on an <a> tag is ignored by browsers for cross-origin
    URLs (which is exactly what Instagram/Facebook/YouTube CDN links
    are) — without this, clicking "Download" just opens the media in
    a new tab instead of saving it.
    """
    if not is_allowed_proxy_url(url):
        raise HTTPException(status_code=400, detail="This host is not allowed for proxied downloads.")

    safe_filename = re.sub(r"[^\w\-. ]", "_", filename).strip()[:100] or "media"
    safe_ext = re.sub(r"[^\w]", "", ext) or "mp4"

    client, upstream = await fetch_allowed_url(url, stream=True, timeout=60, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    })

    if upstream.status_code != 200:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=404, detail="Could not fetch media for download.")

    async def stream():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(
        stream(),
        media_type=upstream.headers.get("content-type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}.{safe_ext}"'},
    )

@app.post("/info")
@limiter.limit("15/minute")
async def get_info(request: Request, body: URLRequest):
    url = body.url.strip()
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
    except Exception:
        raise HTTPException(status_code=400, detail="Could not process this URL. Please try again.")

@app.post("/download")
@limiter.limit("15/minute")
async def download(request: Request, body: URLRequest, format_id: str = "best"):
    platform = detect_platform(body.url)

    # RapidAPI platforms — format_id IS the direct URL
    if platform in ("instagram", "facebook", "youtube") and format_id.startswith("http"):
        return {"download_url": format_id, "title": "media", "ext": "mp4"}

    # yt-dlp platforms
    if not await is_public_http_url(body.url):
        raise HTTPException(status_code=400, detail="This URL cannot be processed.")
    ydl_opts = {"quiet": True, "format": format_id, "skip_download": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(body.url, download=False)
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
    except Exception:
        raise HTTPException(status_code=400, detail="Could not process this download. Please try again.")



