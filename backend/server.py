from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re
import os

app = FastAPI(title="SaveItNow API")

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,https://saveitnow.vercel.app").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

class URLRequest(BaseModel):
    url: str

def detect_platform(url: str) -> str:
    patterns = {
        "Instagram": r"instagram\.com",
        "YouTube":   r"(youtube\.com|youtu\.be)",
        "TikTok":    r"tiktok\.com",
        "Twitter/X": r"(twitter\.com|x\.com)",
        "Facebook":  r"facebook\.com|fb\.watch",
        "Reddit":    r"reddit\.com",
        "Pinterest": r"pinterest\.com",
    }
    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "Video"

def format_size(b):
    if not b: return None
    if b > 1048576: return f"{b/1048576:.1f} MB"
    return f"{b/1024:.0f} KB"

@app.get("/")
def root():
    return {"status": "SaveItNow API is running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/info")
def get_media_info(request: URLRequest):
    url = request.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL — must start with http:// or https://")

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
        if "not available" in msg or "removed" in msg:
            raise HTTPException(status_code=400, detail="This content is no longer available.")
        raise HTTPException(status_code=400, detail="Could not fetch this URL. Make sure it is public and valid.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

    if not info:
        raise HTTPException(status_code=400, detail="No media found at this URL.")

    # Build format list — video qualities
    formats = []
    seen_heights = set()

    raw = info.get("formats") or []
    video_fmts = sorted(
        [f for f in raw if f.get("vcodec") != "none" and f.get("height") and f.get("ext") == "mp4" and f.get("url")],
        key=lambda f: f.get("height", 0),
        reverse=True
    )

    for fmt in video_fmts:
        h = fmt["height"]
        if h in seen_heights: continue
        seen_heights.add(h)
        formats.append({
            "format_id": fmt["format_id"],
            "label": f"{h}p",
            "ext": "mp4",
            "filesize": format_size(fmt.get("filesize")),
        })
        if len(formats) >= 4: break

    # Fallback: any video format
    if not formats:
        video_fmts_any = sorted(
            [f for f in raw if f.get("vcodec") != "none" and f.get("height") and f.get("url")],
            key=lambda f: f.get("height", 0),
            reverse=True
        )
        for fmt in video_fmts_any[:4]:
            h = fmt["height"]
            if h in seen_heights: continue
            seen_heights.add(h)
            formats.append({
                "format_id": fmt["format_id"],
                "label": f"{h}p",
                "ext": fmt.get("ext", "mp4"),
                "filesize": format_size(fmt.get("filesize")),
            })

    # Audio only
    audio_fmts = sorted(
        [f for f in raw if f.get("vcodec") == "none" and f.get("acodec") != "none" and f.get("url")],
        key=lambda f: f.get("abr") or 0,
        reverse=True
    )
    if audio_fmts:
        formats.append({
            "format_id": "bestaudio",
            "label": "Audio Only",
            "ext": "mp3",
            "filesize": format_size(audio_fmts[0].get("filesize")),
        })

    # Last resort fallback
    if not formats and info.get("url"):
        formats.append({
            "format_id": "best",
            "label": "Best Quality",
            "ext": "mp4",
            "filesize": None,
        })

    return {
        "title": info.get("title", "Video"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "platform": detect_platform(url),
        "uploader": info.get("uploader") or info.get("channel"),
        "formats": formats,
    }

@app.post("/download")
def download_media(request: URLRequest, format_id: str = "best"):
    url = request.url.strip()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": format_id if format_id != "bestaudio" else "bestaudio/best",
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Get direct URL
        direct_url = info.get("url")
        if not direct_url and info.get("formats"):
            for f in reversed(info["formats"]):
                if f.get("url"):
                    direct_url = f["url"]
                    break

        if not direct_url:
            raise HTTPException(status_code=404, detail="No downloadable URL found.")

        ext = "mp3" if format_id == "bestaudio" else "mp4"
        return {
            "download_url": direct_url,
            "title": info.get("title", "video"),
            "ext": ext,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
