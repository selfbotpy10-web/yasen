import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="NIRO SELF")

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "web" / "index.html"

@app.get("/")
async def home():
    if not HTML_FILE.exists():
        return JSONResponse(
            {"error": "HTML file not found"},
            status_code=404
        )
    return FileResponse(HTML_FILE)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "NIRO SELF"}
