import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import create_document, get_documents
from schemas import VideoJob

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    docs = get_documents("videojob", {}, min(limit, 100))
    # Convert ObjectId to string if present
    for d in docs:
        if "_id" in d:
            d["_id"] = str(d["_id"]) 
    return {"items": docs}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

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
