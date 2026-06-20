from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import yt_dlp
import httpx
import asyncio
import re

app = FastAPI(title="SaveItNow API")

origins = [
    "http://localhost:3000",
    "https://saveitnow.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

class MediaInfo(BaseModel):
    title: str
    thumbnail: str | None
    duration: int | None
    platform: str
    formats: list[dict]

def detect_platform(url: str) -> str:
    patterns = {
        "instagram": r"instagram\.com",
        "youtube": r"(youtube\.com|youtu\.be)",
        "tiktok": r"tiktok\.com",
        "twitter": r"(twitter\.com|x\.com)",
        "facebook": r"facebook\.com",
        "reddit": r"reddit\.com",
        "pinterest": r"pinterest\.com",
    }
    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "other"

@app.get("/")
def root():
    return {"status": "SaveItNow API is running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/info")
def get_media_info(request: URLRequest):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)

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
                    })

        # Add audio-only option
        formats.append({"format_id": "bestaudio", "label": "Audio Only (MP3)", "ext": "mp3", "filesize": None})

        # Sort by resolution descending
        formats.sort(key=lambda x: int(x["label"].replace("p", "")) if x["label"].endswith("p") else -1, reverse=True)

        return {
            "title": info.get("title", "Unknown"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "platform": detect_platform(request.url),
            "formats": formats[:6],  # limit to top 6
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
def download_media(request: URLRequest, format_id: str = "bestvideo+bestaudio/best"):
    ydl_opts = {
        "quiet": True,
        "format": format_id,
        "merge_output_format": "mp4",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)

        # Get direct URL for streaming
        best_url = None
        if "url" in info:
            best_url = info["url"]
        elif "formats" in info:
            for f in reversed(info["formats"]):
                if f.get("url") and f.get("vcodec") != "none":
                    best_url = f["url"]
                    break

        if not best_url:
            raise HTTPException(status_code=404, detail="No downloadable URL found")

        return {"download_url": best_url, "title": info.get("title", "video"), "ext": "mp4"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
