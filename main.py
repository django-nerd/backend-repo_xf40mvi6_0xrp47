import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

from database import create_document, get_documents, get_document_by_id, update_document
from schemas import VideoJob

# File system paths for generated assets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
AUDIO_DIR = os.path.join(STATIC_DIR, 'audio')
THUMB_DIR = os.path.join(STATIC_DIR, 'thumbnails')

# Ensure directories exist
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static generated files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    return {"message": "YouTube Automation Backend Ready"}

class GenerateRequest(BaseModel):
    niche: str
    style: Optional[str] = "educational"
    duration: Optional[int] = 120
    keywords: Optional[List[str]] = []

@app.post("/api/generate")
def generate_content(payload: GenerateRequest):
    # Simple heuristic content generator (placeholder logic)
    niche = payload.niche.strip()
    if not niche:
        raise HTTPException(status_code=400, detail="Niche/topic is required")

    style = payload.style or "educational"
    duration = max(30, min(int(payload.duration or 120), 900))

    # Title suggestions
    templates = [
        f"{niche}: Rahasia Yang Jarang Dibahas",
        f"{niche} Dalam {duration//60 if duration>=60 else duration} Menit: Ringkas & Padat",
        f"7 Fakta Penting Tentang {niche} Yang Wajib Kamu Tahu",
        f"{niche} Untuk Pemula: Panduan Lengkap",
        f"Kenapa {niche} Itu Penting Di 2025?"
    ]
    title = templates[0]

    # Outline
    outline = [
        "Hook pembuka yang memikat",
        "Perkenalan singkat channel & konteks",
        f"Penjelasan inti tentang {niche}",
        "Tips/praktik terbaik",
        "Contoh kasus nyata",
        "Ringkasan & CTA subscribe"
    ]

    # Script generation (simple stitching)
    script_parts = [
        f"[HOOK] Bayangin kalau kamu bisa memahami {niche} hanya dalam beberapa menit...",
        f"[INTRO] Halo! Di video ini kita bahas {niche} dengan gaya {style}.",
        f"[CONTENT] Intinya, {niche} punya beberapa poin penting: ...",
        "[TIPS] Beberapa tips cepat: 1) ..., 2) ..., 3) ...",
        "[EXAMPLE] Contohnya, ...",
        "[OUTRO] Thanks sudah nonton! Jangan lupa like & subscribe."
    ]
    script = "\n\n".join(script_parts)

    job = VideoJob(
        niche=niche,
        title=title,
        keywords=payload.keywords or [],
        style=style,
        duration=duration,
        outline=outline,
        script=script,
        status="generated",
    )

    job_id = create_document("videojob", job)
    return {"id": job_id, "job": job}

@app.get("/api/jobs")
def list_jobs(limit: int = 20):
    docs = get_documents("videojob", {}, min(limit, 100), sort=[("_id", -1)])
    # Convert ObjectId to string if present
    for d in docs:
        if "_id" in d:
            d["_id"] = str(d["_id"]) 
    return {"items": docs}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

# --- Voice Over (TTS) ---
class TTSRequest(BaseModel):
    job_id: str
    lang: Optional[str] = "id"  # Indonesian default
    slow: Optional[bool] = False

@app.post("/api/tts")
def generate_tts(req: TTSRequest):
    job = get_document_by_id("videojob", req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    script = job.get("script") or ""
    if not script.strip():
        raise HTTPException(status_code=400, detail="Script is empty for this job")

    try:
        from gtts import gTTS
        tts = gTTS(text=script, lang=req.lang or "id", slow=bool(req.slow))
        out_path = os.path.join(AUDIO_DIR, f"{req.job_id}.mp3")
        tts.save(out_path)
        rel_url = f"/static/audio/{req.job_id}.mp3"
        update_document("videojob", req.job_id, {"audio_url": rel_url, "status": "tts_ready"})
        return {"audio_url": rel_url, "status": "tts_ready"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)[:200]}")

# --- Thumbnail Generation (Pillow) ---
class ThumbRequest(BaseModel):
    job_id: str

@app.post("/api/thumbnail")
def generate_thumbnail(req: ThumbRequest):
    job = get_document_by_id("videojob", req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    title = job.get("title") or job.get("niche") or "Video"

    try:
        from PIL import Image, ImageDraw, ImageFont
        # Create image
        W, H = 1280, 720
        img = Image.new("RGB", (W, H), color=(15, 23, 42))  # slate-900
        draw = ImageDraw.Draw(img)
        # Gradient overlay
        for i in range(H):
            ratio = i / H
            r = int(99 + ratio * (30-99))
            g = int(102 + ratio * (64-102))
            b = int(241 + ratio * (175-241))
            draw.line([(0, i), (W, i)], fill=(r, g, b), width=1)
        # Border frame
        draw.rectangle([(20, 20), (W-20, H-20)], outline=(255, 255, 255), width=6)
        # Title text
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 84)
        except Exception:
            font = ImageFont.load_default()
        # Wrap text
        max_width = W - 160
        words = title.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=font) <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        y = H//2 - (len(lines)*96)//2
        for i, line in enumerate(lines[:3]):
            draw.text((80, y + i*96), line, font=font, fill=(255,255,255), stroke_width=3, stroke_fill=(0,0,0))
        # Footer tag
        small = ImageFont.truetype("DejaVuSans.ttf", 36) if hasattr(ImageFont, 'truetype') else ImageFont.load_default()
        draw.text((80, H-100), f"{job.get('style','educational').title()} • {job.get('duration',60)}s", font=small, fill=(240,240,240))

        out_path = os.path.join(THUMB_DIR, f"{req.job_id}.jpg")
        img.save(out_path, format="JPEG", quality=90)
        rel_url = f"/static/thumbnails/{req.job_id}.jpg"
        update_document("videojob", req.job_id, {"thumbnail_url": rel_url, "status": "thumb_ready"})
        return {"thumbnail_url": rel_url, "status": "thumb_ready"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thumbnail failed: {str(e)[:200]}")

# --- YouTube Upload (requires credentials) ---
class UploadRequest(BaseModel):
    job_id: str
    privacy_status: Optional[str] = "unlisted"  # public | unlisted | private

@app.post("/api/upload")
def upload_youtube(req: UploadRequest):
    job = get_document_by_id("videojob", req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check prerequisites
    audio_url = job.get("audio_url")
    if not audio_url:
        raise HTTPException(status_code=400, detail="Audio not found. Generate TTS first.")
    thumb_url = job.get("thumbnail_url")

    # Find local file paths
    audio_path = os.path.join(BASE_DIR, audio_url.lstrip("/")) if audio_url.startswith("/static/") else None
    thumb_path = os.path.join(BASE_DIR, thumb_url.lstrip("/")) if thumb_url and thumb_url.startswith("/static/") else None

    # Attempt to upload using YouTube Data API if credentials exist
    CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRETS", os.path.join(BASE_DIR, "client_secret.json"))
    OAUTH_TOKEN_FILE = os.getenv("GOOGLE_OAUTH_TOKEN", os.path.join(BASE_DIR, "token.json"))

    if not os.path.exists(CLIENT_SECRET_FILE) or not os.path.exists(OAUTH_TOKEN_FILE):
        update_document("videojob", req.job_id, {"upload_status": "requires_credentials"})
        return {
            "status": "requires_credentials",
            "detail": "Google OAuth credentials not found. Provide client_secret.json and token.json.",
        }

    # Prepare video assembly: for demo, upload audio-only as a video with a static thumbnail is non-trivial.
    # Here we will create a simple MP4 slideshow (single frame) using moviepy if available, else error.
    try:
        from moviepy.editor import AudioFileClip, ImageClip
        import tempfile

        if not thumb_path:
            raise Exception("Thumbnail image required to produce a video. Generate thumbnail first.")

        audio_clip = AudioFileClip(audio_path)
        image_clip = ImageClip(thumb_path).set_duration(audio_clip.duration)
        image_clip = image_clip.set_audio(audio_clip)
        video = image_clip.set_fps(24)

        tmpdir = tempfile.mkdtemp()
        video_path = os.path.join(tmpdir, f"{req.job_id}.mp4")
        video.write_videofile(video_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)
    except Exception as e:
        update_document("videojob", req.job_id, {"upload_status": f"render_failed: {str(e)[:120]}"})
        return {"status": "render_failed", "detail": str(e)}

    # Upload to YouTube
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        import json

        with open(OAUTH_TOKEN_FILE, "r") as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
        ])
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": job.get("title") or job.get("niche") or "AI Agent Video",
                "description": job.get("script")[:4000],
                "tags": job.get("keywords", []) or None,
                "categoryId": "22"  # People & Blogs as default
            },
            "status": {"privacyStatus": req.privacy_status or "unlisted"}
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/*")
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
        response = request.execute()
        vid = response.get("id")

        # Set thumbnail if available
        if thumb_path:
            from googleapiclient.http import MediaFileUpload as MFU
            youtube.thumbnails().set(videoId=vid, media_body=MFU(thumb_path)).execute()

        url = f"https://www.youtube.com/watch?v={vid}"
        update_document("videojob", req.job_id, {"youtube_url": url, "upload_status": "uploaded"})
        return {"status": "uploaded", "youtube_url": url}
    except Exception as e:
        update_document("videojob", req.job_id, {"upload_status": f"upload_failed: {str(e)[:120]}"})
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)[:200]}")

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
