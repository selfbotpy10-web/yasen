import os
import json
import hmac
import hashlib
import sqlite3
from urllib.parse import parse_qsl
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="NIRO SELF")

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "web" / "index.html"
DB_PATH = os.getenv("DB_PATH", "niro_self.sqlite3")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS web_settings (
            user_id INTEGER PRIMARY KEY,
            settings TEXT NOT NULL DEFAULT '{}'
        )
        """)

init_db()

def verify_telegram_data(init_data):
    if not BOT_TOKEN or not init_data:
        return None

    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", None)

    if not received_hash:
        return None

    check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(data.items())
    )

    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    user_data = data.get("user")

    if not user_data:
        return None

    try:
        user = json.loads(user_data)
        return user
    except Exception:
        return None

def authenticated_user(init_data):
    user = verify_telegram_data(init_data)

    if not user or not user.get("id"):
        raise HTTPException(
            status_code=401,
            detail="تأیید هویت تلگرام نامعتبر است"
        )

    return user

@app.get("/")
async def home():
    if not HTML_FILE.exists():
        raise HTTPException(404, "index.html not found")
    return FileResponse(HTML_FILE)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "NIRO SELF"}

@app.get("/api/me")
async def me(authorization: str = Header(default="")):
    init_data = authorization.replace("tma ", "", 1)
    user = authenticated_user(init_data)

    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "first_name": user.get("first_name", ""),
            "username": user.get("username", "")
        }
    }

class SettingsInput(BaseModel):
    settings: dict

@app.get("/api/settings")
async def get_settings(authorization: str = Header(default="")):
    init_data = authorization.replace("tma ", "", 1)
    user = authenticated_user(init_data)

    with db() as con:
        row = con.execute(
            "SELECT settings FROM web_settings WHERE user_id=?",
            (user["id"],)
        ).fetchone()

    settings = json.loads(row[0]) if row else {}

    return {"ok": True, "settings": settings}

@app.post("/api/settings")
async def save_settings(
    payload: SettingsInput,
    authorization: str = Header(default="")
):
    init_data = authorization.replace("tma ", "", 1)
    user = authenticated_user(init_data)

    allowed = {
        "bio_clock",
        "surname_clock",
        "auto_reply",
        "reply_text",
        "media_save",
        "clock_style"
    }

    settings = {
        key: value
        for key, value in payload.settings.items()
        if key in allowed
    }

    with db() as con:
        con.execute("""
            INSERT INTO web_settings(user_id, settings)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET settings=excluded.settings
        """, (user["id"], json.dumps(settings, ensure_ascii=False)))

    return {"ok": True, "message": "تنظیمات ذخیره شد"}


# ---------- NIRO PHONE AGENT STATUS ----------
AGENT_SECRET = os.getenv("NIRO_AGENT_SECRET", "")

with db() as con:
    con.execute("""
        CREATE TABLE IF NOT EXISTS agent_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            authorized INTEGER NOT NULL DEFAULT 0,
            device TEXT NOT NULL DEFAULT 'Termux',
            last_seen TEXT,
            detail TEXT NOT NULL DEFAULT ''
        )
    """)

class AgentHeartbeat(BaseModel):
    authorized: bool
    device: str = "Termux"
    detail: str = ""

def verify_agent_secret(secret):
    if not AGENT_SECRET or not hmac.compare_digest(
        secret, AGENT_SECRET
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/api/agent/heartbeat")
async def agent_heartbeat(
    payload: AgentHeartbeat,
    x_agent_secret: str = Header(default="", alias="X-NIRO-AGENT-SECRET")
):
    verify_agent_secret(x_agent_secret)

    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).isoformat()

    with db() as con:
        con.execute("""
            INSERT INTO agent_status
                (id, authorized, device, last_seen, detail)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                authorized=excluded.authorized,
                device=excluded.device,
                last_seen=excluded.last_seen,
                detail=excluded.detail
        """, (
            int(payload.authorized),
            payload.device[:40],
            now_utc,
            payload.detail[:200]
        ))

    return {"ok": True}

@app.get("/api/agent/status")
async def agent_status(
    x_agent_secret: str = Header(default="", alias="X-NIRO-AGENT-SECRET")
):
    verify_agent_secret(x_agent_secret)

    with db() as con:
        row = con.execute("""
            SELECT authorized, device, last_seen, detail
            FROM agent_status WHERE id=1
        """).fetchone()

    if not row:
        return {"online": False, "authorized": False, "last_seen": None}

    from datetime import datetime, timezone, timedelta
    seen = datetime.fromisoformat(row[2])
    online = datetime.now(timezone.utc) - seen < timedelta(seconds=120)

    return {
        "online": online,
        "authorized": bool(row[0]) if online else False,
        "device": row[1],
        "last_seen": row[2],
        "detail": row[3] if online else "Agent heartbeat expired"
    }
