import os
import re
import sqlite3
import logging
import asyncio
import secrets
import io
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
)
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# ===================== تنظیمات =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "توکن_ربات_را_اینجا_بگذار")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(";", ",").split(",") if x.strip().isdigit()}
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
CARD_NUMBER = os.getenv("CARD_NUMBER", "شماره کارت را اینجا قرار دهید")
CARD_OWNER = os.getenv("CARD_OWNER", "نام صاحب کارت")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "your_support")
BET_GROUP_ID = int(os.getenv("BET_GROUP_ID", "0") or 0)
BET_GROUP_LINK = os.getenv("BET_GROUP_LINK", "https://t.me/")
BET_TAX_PERCENT = int(os.getenv("BET_TAX_PERCENT", "10") or 10)
BET_TAX_PERCENT = max(0, min(100, BET_TAX_PERCENT))
DB_PATH = os.getenv("DB_PATH", "niro_self.sqlite3")
GAME_IMAGE_PATH = os.getenv("GAME_IMAGE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_start.png"))
WALLET_TEMPLATE = os.getenv("WALLET_TEMPLATE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallet_template.png"))
DIAMOND_TOMAN_RATE = int(os.getenv("DIAMOND_TOMAN_RATE", "50") or 50)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger("NIRO-SELF")

# ===================== دیتابیس =====================
def db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            diamonds INTEGER NOT NULL DEFAULT 0, blocked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS purchases(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
            status TEXT DEFAULT 'pending', photo_file_id TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
            kind TEXT, note TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS referrals(
            invited_id INTEGER PRIMARY KEY, referrer_id INTEGER, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS games(
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, message_id INTEGER,
            creator_id INTEGER, opponent_id INTEGER, stake INTEGER,
            status TEXT DEFAULT 'waiting', created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        """)

def register_user(user):
    with db() as c:
        c.execute("""INSERT INTO users(user_id,username,first_name,created_at)
        VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
        username=excluded.username, first_name=excluded.first_name""",
        (user.id, user.username or "", user.first_name or "", datetime.utcnow().isoformat()))

def user_row(uid):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def balance(uid):
    if uid == OWNER_ID and OWNER_ID:
        return None  # مالک: نامحدود
    row = user_row(uid)
    return row["diamonds"] if row else 0

def add_tx(uid, amount, kind, note=""):
    with db() as c:
        c.execute("UPDATE users SET diamonds=diamonds+? WHERE user_id=?", (amount, uid))
        c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",
                  (uid, amount, kind, note, datetime.utcnow().isoformat()))

def change_balance(uid, amount, kind, note=""):
    if uid == OWNER_ID and OWNER_ID:
        return True
    with db() as c:
        row = c.execute("SELECT diamonds FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row:
            return False
        if amount < 0 and row["diamonds"] < -amount:
            return False
        c.execute("UPDATE users SET diamonds=diamonds+? WHERE user_id=?", (amount, uid))
        c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",
                  (uid, amount, kind, note, datetime.utcnow().isoformat()))
        return True

def is_admin(uid):
    return uid in ADMIN_IDS or (OWNER_ID and uid == OWNER_ID)

def money_text(uid):
    b = balance(uid)
    return "♾ نامحدود (مالک ربات)" if b is None else f"💎 {b:,} الماس"


FONT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")


def _card_font(size, bold=False):
    # Prefer fonts shipped beside bot.py, then system fonts.
    candidates = []
    local = FONT_BOLD if bold else FONT_REGULAR
    candidates.extend([local, os.path.join(FONT_DIR, "fonts", os.path.basename(local))])
    candidates.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ])
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Last-resort default font; _card_text will sanitize unsupported characters.
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _card_text(draw, xy, text, size, fill, bold=False, anchor="mm", stroke_width=0, stroke_fill=None):
    text = str(text)
    font = _card_font(size, bold)
    kwargs = {"font": font, "fill": fill, "anchor": anchor, "stroke_width": stroke_width}
    if stroke_fill is not None:
        kwargs["stroke_fill"] = stroke_fill
    # Try shaping Persian/Arabic when Pillow was built with RAQM support.
    rtl = any("\\u0600" <= ch <= "\\u06ff" for ch in text)
    try:
        if rtl:
            draw.text(xy, text, direction="rtl", language="fa", **kwargs)
        else:
            draw.text(xy, text, **kwargs)
        return
    except (TypeError, ValueError, UnicodeEncodeError, OSError):
        pass
    # If RAQM/characters are unavailable, retry plain drawing. If the font
    # cannot encode some glyphs, keep the card alive and replace those glyphs.
    try:
        draw.text(xy, text, **kwargs)
        return
    except (TypeError, ValueError, UnicodeEncodeError, OSError):
        pass
    safe = "".join(ch if ord(ch) < 128 else "?" for ch in text)
    try:
        draw.text(xy, safe, **kwargs)
    except Exception:
        # A decorative text failure must never crash a group bet.
        return

def wallet_card_bytes(user, diamonds, toman, profile_bytes=None):
    """Render a personalized wallet card on the supplied VIP template."""
    base_path = WALLET_TEMPLATE
    if os.path.isfile(base_path):
        canvas = Image.open(base_path).convert("RGB")
    else:
        canvas = Image.new("RGB", (900, 1000), (12, 8, 28))
    w, h = canvas.size
    draw = ImageDraw.Draw(canvas)
    font = _card_font
    # Mask example text areas with matching dark panels, preserving the neon frame.
    draw.rounded_rectangle((int(w*.46), int(h*.19), int(w*.89), int(h*.46)), radius=24, fill=(8,7,17), outline=(125,63,196), width=max(2,w//450))
    draw.rounded_rectangle((int(w*.06), int(h*.49), int(w*.49), int(h*.65)), radius=28, fill=(8,7,17), outline=(138,79,225), width=max(2,w//450))
    draw.rounded_rectangle((int(w*.51), int(h*.49), int(w*.94), int(h*.65)), radius=28, fill=(8,7,17), outline=(224,164,52), width=max(2,w//450))
    draw.rounded_rectangle((int(w*.13), int(h*.68), int(w*.87), int(h*.81)), radius=25, fill=(8,7,17), outline=(138,79,225), width=max(2,w//450))
    # Replace portrait with the Telegram user's profile photo.
    if profile_bytes:
        try:
            photo=Image.open(io.BytesIO(profile_bytes)).convert("RGB")
            side=min(photo.size); x=(photo.width-side)//2; y=(photo.height-side)//2
            photo=photo.crop((x,y,x+side,y+side)).resize((int(w*.30),int(w*.30)))
            mask=Image.new("L",photo.size,0); ImageDraw.Draw(mask).ellipse((2,2,photo.width-3,photo.height-3),fill=255)
            px,py=int(w*.105),int(h*.205)
            canvas.paste(photo,(px,py),mask)
            draw=ImageDraw.Draw(canvas)
            draw.ellipse((px-5,py-5,px+photo.width+5,py+photo.height+5),outline=(180,78,255),width=max(4,w//220))
        except Exception: pass
    # Name and ID
    name=(user.full_name or user.first_name or "کاربر")[:26]
    _card_text(draw, (int(w*.67), int(h*.235)),name, int(w*.038), bold=False, fill=(255,218,99),anchor="mm",stroke_width=1,stroke_fill=(35,10,30))
    _card_text(draw, (int(w*.67), int(h*.32)),f"ID: {user.id}", int(w*.032), bold=False, fill=(240,235,255),anchor="mm")
    if user.username:
        _card_text(draw, (int(w*.67), int(h*.39)),f"@{user.username[:24]}", int(w*.025), bold=False, fill=(186,157,255),anchor="mm")
    d_text="∞" if diamonds is None else f"{diamonds:,}"
    t_text="نامحدود" if toman is None else f"{toman:,}"
    _card_text(draw, (int(w*.28), int(h*.535)),d_text, int(w*.064), bold=True, fill=(75,185,255),anchor="mm",stroke_width=1,stroke_fill=(3,22,55))
    _card_text(draw, (int(w*.28), int(h*.615)),"موجودی الماس", int(w*.030), bold=False, fill=(240,230,255),anchor="mm")
    _card_text(draw, (int(w*.73), int(h*.535)),t_text, int(w*.050), bold=True, fill=(255,230,180),anchor="mm")
    _card_text(draw, (int(w*.73), int(h*.615)),"موجودی به تومان", int(w*.030), bold=False, fill=(240,230,255),anchor="mm")
    _card_text(draw, (int(w*.50), int(h*.735)),"وضعیت حساب: فعال", int(w*.036), bold=False, fill=(110,255,120),anchor="mm")
    out=io.BytesIO(); canvas.save(out,format="PNG"); out.seek(0)
    return out



async def fetch_profile_bytes(bot, uid):
    try:
        photos = await bot.get_user_profile_photos(uid, limit=1)
        if photos.total_count:
            f = await bot.get_file(photos.photos[0][-1].file_id)
            return bytes(await f.download_as_bytearray())
    except Exception as exc:
        log.info("profile photo fetch skipped for %s: %s", uid, exc)
    return None

def game_card_bytes(creator, opponent, stake, tax_percent=BET_TAX_PERCENT, status="waiting", creator_photo=None, opponent_photo=None):
    """Create a wager card in the same NIRO purple/gold wallet-card style."""
    canvas = Image.open(WALLET_TEMPLATE).convert("RGB") if os.path.isfile(WALLET_TEMPLATE) else Image.new("RGB", (900, 1000), (12, 8, 28))
    w, h = canvas.size
    draw = ImageDraw.Draw(canvas)
    font = _card_font
    # Reuse the template's ornamental frame; replace its wallet-specific panels.
    draw.rounded_rectangle((int(w*.06), int(h*.17), int(w*.94), int(h*.47)), radius=28, fill=(5,5,15), outline=(150,70,225), width=max(3,w//350))
    draw.rounded_rectangle((int(w*.06), int(h*.49), int(w*.49), int(h*.65)), radius=26, fill=(5,5,15), outline=(70,160,255), width=max(3,w//350))
    draw.rounded_rectangle((int(w*.51), int(h*.49), int(w*.94), int(h*.65)), radius=26, fill=(5,5,15), outline=(230,170,55), width=max(3,w//350))
    draw.rounded_rectangle((int(w*.13), int(h*.68), int(w*.87), int(h*.81)), radius=26, fill=(5,5,15), outline=(150,70,225), width=max(3,w//350))
    # Update title area without changing the template's neon/gold look.
    draw.rounded_rectangle((int(w*.24), int(h*.075), int(w*.76), int(h*.145)), radius=20, fill=(8,5,20), outline=(225,165,55), width=max(2,w//500))
    draw.text((w//2, int(h*.11)), "VIP BET ARENA", font=font(int(w*.052), True), fill=(255,205,75), anchor="mm")
    def paste_avatar(data, cx, cy, diameter):
        if data:
            try:
                im=Image.open(io.BytesIO(data)).convert("RGB")
                side=min(im.size); im=im.crop(((im.width-side)//2,(im.height-side)//2, (im.width+side)//2,(im.height+side)//2)).resize((diameter,diameter))
                mask=Image.new("L",(diameter,diameter),0); ImageDraw.Draw(mask).ellipse((2,2,diameter-3,diameter-3),fill=255)
                canvas.paste(im,(cx-diameter//2,cy-diameter//2),mask)
            except Exception: pass
        draw.ellipse((cx-diameter//2-5,cy-diameter//2-5,cx+diameter//2+5,cy+diameter//2+5),outline=(190,80,255),width=max(4,w//230))
    diameter=int(w*.19); cy=int(h*.285)
    paste_avatar(creator_photo,int(w*.28),cy,diameter)
    paste_avatar(opponent_photo,int(w*.72),cy,diameter)
    c_name=(creator.full_name or creator.first_name or "میزبان")[:18]
    o_name=(opponent.full_name or opponent.first_name or "حریف")[:18] if opponent else "منتظر حریف"
    _card_text(draw, (int(w*.28), int(h*.39)),c_name, int(w*.031), bold=True, fill=(255,220,95),anchor="mm")
    _card_text(draw, (int(w*.28), int(h*.435)),f"ID: {creator.id}", int(w*.025), bold=True, fill=(245,235,255),anchor="mm")
    _card_text(draw, (int(w*.72), int(h*.39)),o_name, int(w*.031), bold=True, fill=(255,220,95),anchor="mm")
    _card_text(draw, (int(w*.72), int(h*.435)),f"ID: {opponent.id}" if opponent else "حریف هنوز وارد نشده", int(w*.023), bold=True, fill=(245,235,255),anchor="mm")
    tax=(stake*2*tax_percent)//100 if opponent else 0
    prize=stake*2-tax if opponent else stake*2
    _card_text(draw, (int(w*.28), int(h*.535)),f"{stake:,}", int(w*.058), bold=True, fill=(80,185,255),anchor="mm")
    _card_text(draw, (int(w*.28), int(h*.615)),"شرط هر بازیکن • الماس", int(w*.027), bold=True, fill=(245,235,255),anchor="mm")
    _card_text(draw, (int(w*.73), int(h*.535)),f"{prize:,}", int(w*.048), bold=True, fill=(255,220,150),anchor="mm")
    _card_text(draw, (int(w*.73), int(h*.615)),"جایزه خالص برنده" if opponent else "جایزه احتمالی • الماس", int(w*.027), bold=True, fill=(245,235,255),anchor="mm")
    state="رقابت در جریان" if opponent else "چالش آماده • منتظر حریف"
    _card_text(draw, (w//2,int(h*.735)), state, int(w*.037), bold=True, fill=(110,255,130),anchor="mm")
    _card_text(draw, (w//2,int(h*.78)), f"مالیات: {tax:,} الماس • نرخ {tax_percent}٪" if opponent else f"مالیات {tax_percent}٪ فقط پس از تکمیل بازی", int(w*.028), bold=True, fill=(230,200,255),anchor="mm")
    out=io.BytesIO(); canvas.save(out,format="PNG"); out.seek(0); return out

async def send_wallet(update, context, user):
    uid=user.id
    b=balance(uid)
    toman=None if b is None else b*DIAMOND_TOMAN_RATE
    photo_bytes=None
    try:
        photos=await context.bot.get_user_profile_photos(uid, limit=1)
        if photos.total_count:
            file=await context.bot.get_file(photos.photos[0][-1].file_id)
            photo_bytes=await file.download_as_bytearray()
    except Exception as exc:
        log.info("profile photo fetch skipped: %s",exc)
    card=wallet_card_bytes(user,b,toman,photo_bytes)
    diamonds_label="نامحدود" if b is None else f"{b:,}"
    toman_label="نامحدود" if toman is None else f"{toman:,}"
    caption=("👑 <b>𝐍𝐈𝐑𝐎 • 𝐕𝐈𝐏 𝐖𝐀𝐋𝐋𝐄𝐓</b>\n\n"
            "✨ کیف پول اختصاصی شما به‌روز شد.\n"
            "🛡️ اطلاعات حساب و موجودی به‌صورت زنده نمایش داده می‌شود.\n\n"
            f"👤 <b>کاربر:</b> {user.full_name}\n"
            f"🆔 <code>{uid}</code>\n"
            f"💎 <b>موجودی:</b> {diamonds_label} الماس\n"
            f"💰 <b>ارزش تقریبی:</b> {toman_label} تومان\n\n"
            "💜 با آرزوی موفقیت در NIRO VIP")
    keyboard=InlineKeyboardMarkup([[InlineKeyboardButton(f"💎 {diamonds_label} الماس  |  💰 {toman_label} تومان",callback_data="wallet_details")],
                                  [InlineKeyboardButton("🔙 منوی اصلی",callback_data="home")]])
    if update.message:
        await update.message.reply_photo(photo=card,caption=caption,parse_mode=ParseMode.HTML,reply_markup=keyboard)
    elif update.callback_query:
        q=update.callback_query
        await q.answer()
        await q.message.reply_photo(photo=card,caption=caption,parse_mode=ParseMode.HTML,reply_markup=keyboard)


def record_bet_tax(amount, game_id):
    """Record cumulative bot tax without crediting a spendable user balance."""
    if amount <= 0:
        return
    with db() as c:
        row = c.execute("SELECT value FROM settings WHERE key=\'bet_tax_total\'").fetchone()
        total = int(row["value"] if row else 0) + amount
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(\'bet_tax_total\',?)", (str(total),))
        c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",
                  (0, amount, "bet_tax", f"مالیات بازی {game_id} ({BET_TAX_PERCENT}%)", datetime.utcnow().isoformat()))

def bet_tax_total():
    with db() as c:
        row = c.execute("SELECT value FROM settings WHERE key=\'bet_tax_total\'").fetchone()
        return int(row["value"] if row else 0)

# ===================== متن‌ها و منو =====================
WELCOME = (
    "╔═══『 <b>𝐍𝐈𝐑𝐎 𝐒𝐄𝐋𝐅 • 𝐕𝐈𝐏</b> 』═══╗\n\n"
    "👑 <b>به NIRO SELF خوش آمدی!</b>\n"
    "💎 مرکز خدمات و مدیریت حساب اختصاصی تو\n\n"
    "✅ موجودی الماس خود را مدیریت کن\n"
    "✅ در گروه‌های مجاز با دوستانت بازی کن\n"
    "✅ با دعوت دوستان، الماس هدیه بگیر\n"
    "🛡️ پشتیبانی و خدمات همیشه در دسترس است\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🚀 <b>از منوی زیر، بخش موردنظرت را انتخاب کن.</b>\n"
    "╚═══════ <b>𝐕𝐈𝐏</b> ═══════╝"
)

def main_keyboard():
    # Telegram inline buttons do not support custom colors; use bold icon/color-coded emoji labels.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 فعال‌سازی سلف ✨", callback_data="self"),
         InlineKeyboardButton("🎮 مرکز بازی و گروه", callback_data="group")],
        [InlineKeyboardButton("👤 حساب من", callback_data="account"),
         InlineKeyboardButton("💎 خرید الماس", callback_data="buy")],
        [InlineKeyboardButton("🎁 هدیه و دعوت", callback_data="free"),
         InlineKeyboardButton("⚙️ کانفیگ", callback_data="config")],
        [InlineKeyboardButton("🆘 پشتیبانی", callback_data="help")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    register_user(u)
    # لینک دعوت فقط برای کاربر تازه‌وارد و فقط یک‌بار
    if context.args and context.args[0].isdigit():
        ref = int(context.args[0])
        if ref != u.id and ref != OWNER_ID:
            with db() as c:
                old = c.execute("SELECT invited_id FROM referrals WHERE invited_id=?", (u.id,)).fetchone()
                ref_exists = c.execute("SELECT user_id FROM users WHERE user_id=?", (ref,)).fetchone()
                if not old and ref_exists:
                    c.execute("INSERT INTO referrals(invited_id,referrer_id,created_at) VALUES(?,?,?)",
                              (u.id, ref, datetime.utcnow().isoformat()))
                    awarded_referrer = ref
                else:
                    awarded_referrer = None
            if awarded_referrer:
                add_tx(awarded_referrer, 50, "referral", f"دعوت کاربر {u.id}")
                try:
                    await context.bot.send_message(awarded_referrer, "🎉 یک دوست با لینک اختصاصی تو وارد NIRO SELF شد و ۵۰ الماس هدیه گرفتی!")
                except Exception:
                    pass
    if user_row(u.id)["blocked"]:
        await update.message.reply_text("⛔ دسترسی حساب شما محدود شده است.")
        return
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())

async def account(update, context):
    q = update.callback_query
    await q.answer()
    u = q.from_user
    row = user_row(u.id)
    text = (
        "╔══『 <b>👤 حساب کاربری • 𝐕𝐈𝐏</b> 』══╗\n\n"
        f"🪪 <b>شناسه:</b> <code>{u.id}</code>\n"
        f"🌐 <b>نام کاربری:</b> @{u.username or 'ندارد'}\n"
        f"💎 <b>موجودی:</b> {money_text(u.id)}\n"
        f"📅 <b>عضویت از:</b> {row['created_at'][:10] if row and row['created_at'] else '—'}\n"
        "🟢 <b>وضعیت حساب:</b> فعال\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎁 با دعوت دوستان الماس بیشتری دریافت کن.\n"
        "╚═══════ <b>𝐍𝐈𝐑𝐎 𝐕𝐈𝐏</b> ═══════╝"
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]))

async def show_section(update, context):
    q = update.callback_query
    await q.answer()
    key = q.data
    if key == "account":
        return await send_wallet(update, context, q.from_user)
    if key == "self":
        text = "╔══『 <b>🛠 فعال‌سازی سلف • 𝐕𝐈𝐏</b> 』══╗\n\n💠 این قابلیت در حال آماده‌سازی نسخه جدید است.\n🔔 پس از تکمیل، اطلاع‌رسانی خواهد شد.\n╚═══════ <b>𝐍𝐈𝐑𝐎</b> ═══════╝"
        kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    elif key == "config":
        text = "╔══『 <b>⚙️ کانفیگ • 𝐕𝐈𝐏</b> 』══╗\n\n💠 این خدمت در حال آماده‌سازی است.\n✨ به‌زودی در NIRO SELF فعال می‌شود.\n╚═══════ <b>𝐍𝐈𝐑𝐎</b> ═══════╝"
        kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    elif key == "group":
        text = ("╔══『 <b>🎮 مرکز بازی • 𝐕𝐈𝐏</b> 』══╗\n\n"
                "👑 برای بازی و انتقال الماس، ربات را در گروه ادمین کن.\n"
                "🎲 دستورها: «بازی ۲۰»، «موجودی» و «انتقال ۲۰»\n"
                f"🧾 مالیات هر رقابت: {BET_TAX_PERCENT}% از مجموع شرط‌ها (فقط بازی تکمیل‌شده)\n"
                "╚═══════ <b>𝐍𝐈𝐑𝐎</b> ═══════╝")
        kb = [[InlineKeyboardButton("🔗 ورود به گروه شرط‌بندی", url=BET_GROUP_LINK)],
              [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    elif key == "free":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={q.from_user.id}"
        text = ("╔══『 <b>🎁 باشگاه دعوت • 𝐕𝐈𝐏</b> 』══╗\n\n"
                "👑 دوستانت را به خانواده NIRO دعوت کن.\n"
                "💎 پاداش هر کاربر جدید و یکتا: <b>۵۰ الماس</b>\n"
                "🔒 هر کاربر فقط یک‌بار پاداش دعوت دارد.\n\n"
                f"🔗 <b>لینک اختصاصی:</b>\n<code>{link}</code>\n\n"
                "✨ لینک را بفرست و هدیه‌ات را دریافت کن.\n"
                "╚═══════ <b>𝐍𝐈𝐑𝐎</b> ═══════╝")
        kb = [[InlineKeyboardButton("📤 اشتراک‌گذاری لینک", url=f"https://t.me/share/url?url={link}")],
              [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    elif key == "help":
        text = "╔══『 <b>🆘 راهنما و پشتیبانی • 𝐕𝐈𝐏</b> 』══╗\n\n💠 یکی از گزینه‌های زیر را انتخاب کن.\n╚═══════ <b>𝐍𝐈𝐑𝐎</b> ═══════╝"
        kb = [[InlineKeyboardButton("📖 راهنمای فعال‌سازی سلف", callback_data="guide")],
              [InlineKeyboardButton("🎧 ارتباط با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
              [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    else:
        return
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def guide(update, context):
    q = update.callback_query
    await q.answer()
    text = ("╔══『 <b>📖 راهنمای سلف • 𝐕𝐈𝐏</b> 』══╗\n\n"
            "1️⃣ وضعیت حساب و دسترسی خود را بررسی کن.\n"
            "2️⃣ اطلاعات را فقط در بخش رسمی ربات وارد کن.\n"
            "3️⃣ این بخش تا انتشار نسخه پایدار غیرفعال است.\n"
            "4️⃣ اطلاعیه‌های ربات را دنبال کن.\n\n"
            "🛡️ کدها و اطلاعات ورود محرمانه را برای هیچ‌کس ارسال نکن.\n"
            "╚═══════ <b>𝐍𝐈𝐑𝐎</b> ═══════╝")
    await q.edit_message_text(text, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="help")]]))

# ===================== خرید الماس =====================
def keypad(amount):
    rows = []
    for n in (1, 2, 3):
        pass
    rows = [
        [InlineKeyboardButton(str(n), callback_data=f"digit:{n}") for n in (1,2,3)],
        [InlineKeyboardButton(str(n), callback_data=f"digit:{n}") for n in (4,5,6)],
        [InlineKeyboardButton(str(n), callback_data=f"digit:{n}") for n in (7,8,9)],
        [InlineKeyboardButton("🧹 پاک‌کردن", callback_data="digit:clear"),
         InlineKeyboardButton("۰", callback_data="digit:0"),
         InlineKeyboardButton("⌫", callback_data="digit:back")],
        [InlineKeyboardButton("✅ تأیید مقدار", callback_data="buy_confirm"),
         InlineKeyboardButton("❌ لغو", callback_data="buy_cancel")]
    ]
    return InlineKeyboardMarkup(rows)

async def buy_start(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["buy_amount"] = ""
    await q.edit_message_text(
        "╔══『 <b>💎 درگاه خرید • 𝐕𝐈𝐏</b> 』══╗\n\n"
        "💠 مقدار الماس موردنیاز را انتخاب کن.\n"
        "🔐 پس از تأیید، اطلاعات پرداخت نمایش داده می‌شود.\n"
        "╚═══════ <b>𝐍𝐈𝐑𝐎</b> ═══════╝",
        parse_mode=ParseMode.HTML, reply_markup=keypad("")
    )

async def buy_callbacks(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "buy_cancel":
        context.user_data.pop("buy_amount", None)
        return await q.edit_message_text("خرید لغو شد.", reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="home")]]))
    if data.startswith("digit:"):
        val = data.split(":",1)[1]
        s = context.user_data.get("buy_amount", "")
        if val == "clear": s = ""
        elif val == "back": s = s[:-1]
        elif len(s) < 9: s += val
        context.user_data["buy_amount"] = s
        return await q.edit_message_text(
            f"💎 <b>مقدار انتخاب‌شده:</b> {s or '۰'}\n\nعدد موردنظر را وارد کن و تأیید بزن.",
            parse_mode=ParseMode.HTML, reply_markup=keypad(s))
    if data == "buy_confirm":
        s = context.user_data.get("buy_amount", "")
        if not s or int(s) <= 0:
            return await q.answer("ابتدا مقدار معتبر وارد کن.", show_alert=True)
        amount = int(s)
        context.user_data["pending_amount"] = amount
        text = (f"╔══『 <b>💳 پرداخت • 𝐕𝐈𝐏</b> 』══╗\n\n"
                f"💎 <b>سفارش:</b> {amount:,} الماس\n"
                f"🏦 <b>شماره کارت:</b> <code>{CARD_NUMBER}</code>\n"
                f"👤 <b>صاحب کارت:</b> {CARD_OWNER}\n\n"
                "📸 تصویر واضح رسید را پس از پرداخت ارسال کن.\n"
                "🔒 الماس پس از تأیید مدیریت به حسابت افزوده می‌شود.\n"
                "╚═══════ <b>𝐍𝐈𝐑𝐎 𝐕𝐈𝐏</b> ═══════╝")
        context.user_data["state"] = "receipt"
        return await q.edit_message_text(text, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو خرید", callback_data="buy_cancel")]]))

async def receipt_photo(update, context):
    uid = update.effective_user.id
    if context.user_data.get("state") != "receipt":
        return
    if not update.message.photo:
        return await update.message.reply_text("لطفاً تصویر رسید پرداخت را به‌صورت عکس ارسال کن.")
    amount = int(context.user_data.get("pending_amount", 0))
    file_id = update.message.photo[-1].file_id
    with db() as c:
        cur = c.execute("INSERT INTO purchases(user_id,amount,photo_file_id,created_at) VALUES(?,?,?,?)",
                        (uid, amount, file_id, datetime.utcnow().isoformat()))
        pid = cur.lastrowid
    context.user_data.pop("state", None)
    context.user_data.pop("pending_amount", None)
    await update.message.reply_text("✅ رسیدت ثبت شد و برای بررسی به مدیریت ارسال شد.\nپس از بررسی نتیجه به تو اطلاع داده می‌شود.")
    for admin in ADMIN_IDS | ({OWNER_ID} if OWNER_ID else set()):
        try:
            await context.bot.send_photo(
                admin, file_id,
                caption=f"🧾 درخواست خرید #{pid}\nکاربر: {uid}\nمقدار: {amount:,} الماس\nوضعیت: در انتظار بررسی",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ تأیید و واریز", callback_data=f"purchase:{pid}:approve"),
                    InlineKeyboardButton("❌ رد درخواست", callback_data=f"purchase:{pid}:reject")
                ]])
            )
        except Exception as e:
            log.warning("ارسال رسید به ادمین ناموفق: %s", e)

async def purchase_review(update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        return await q.answer("دسترسی ادمین لازم است.", show_alert=True)
    await q.answer()
    _, pid, action = q.data.split(":")
    with db() as c:
        p = c.execute("SELECT * FROM purchases WHERE id=?", (int(pid),)).fetchone()
        if not p or p["status"] != "pending":
            return await q.answer("این درخواست قبلاً بررسی شده است.", show_alert=True)
        if action == "approve":
            c.execute("UPDATE purchases SET status='approved' WHERE id=?", (int(pid),))
            c.execute("UPDATE users SET diamonds=diamonds+? WHERE user_id=?", (p["amount"], p["user_id"]))
            c.execute("INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",
                      (p["user_id"], p["amount"], "purchase", f"خرید #{pid}", datetime.utcnow().isoformat()))
        else:
            c.execute("UPDATE purchases SET status='rejected' WHERE id=?", (int(pid),))
    if action == "approve":
        await context.bot.send_message(p["user_id"], f"🎉 پرداختت تأیید شد!\n💎 {p['amount']:,} الماس با موفقیت به حسابت اضافه شد.")
        label = "✅ خرید تأیید شد و الماس واریز گردید."
    else:
        await context.bot.send_message(p["user_id"], "⚠️ رسید خرید تأیید نشد.\nممکن است تصویر رسید معتبر نباشد یا در بررسی پرداخت مشکلی وجود داشته باشد. در صورت نیاز با پشتیبانی تماس بگیر.")
        label = "❌ درخواست خرید رد شد."
    await q.edit_message_caption((q.message.caption or "") + "\n\n" + label, reply_markup=None)

# ===================== پنل ادمین =====================
def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊  آمار و گزارش", callback_data="adm:stats"),
         InlineKeyboardButton("⚙️  تنظیمات", callback_data="adm:settings")],
        [InlineKeyboardButton("🟢  شارژ کاربر", callback_data="adm:add"),
         InlineKeyboardButton("🔴  کسر الماس", callback_data="adm:sub")],
        [InlineKeyboardButton("📣  ارسال همگانی", callback_data="adm:broadcast"),
         InlineKeyboardButton("🎁  هدیه به همه", callback_data="adm:gift")],
        [InlineKeyboardButton("✉️  پیام اختصاصی", callback_data="adm:message")],
        [InlineKeyboardButton("🚫  محدودسازی", callback_data="adm:block"),
         InlineKeyboardButton("🔓  رفع محدودیت", callback_data="adm:unblock")],
        [InlineKeyboardButton("🔴  توقف سلف", callback_data="adm:selfoff"),
         InlineKeyboardButton("🟢  فعال‌سازی سلف", callback_data="adm:selfon")],
        [InlineKeyboardButton("⏸  توقف ربات", callback_data="adm:off"),
         InlineKeyboardButton("▶️  راه‌اندازی", callback_data="adm:on")],
        [InlineKeyboardButton("🏠  بازگشت به منوی اصلی", callback_data="home")]
    ])

async def admin_command(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ دسترسی غیرمجاز.")
    with db() as c:
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('bot_enabled','1')")
    await update.message.reply_text("╔══『 <b>🛡 پنل مدیریت • 𝐕𝐈𝐏</b> 』══╗\n\n👑 ابزارهای مدیریتی و گزارش سیستم\n╚═══════ <b>𝐍𝐈𝐑𝐎</b> ═══════╝",
                                    parse_mode=ParseMode.HTML, reply_markup=admin_kb())

async def admin_callbacks(update, context):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        return await q.answer("دسترسی غیرمجاز.", show_alert=True)
    await q.answer()
    action = q.data.split(":")[1]
    if action == "stats":
        with db() as c:
            users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
            total = c.execute("SELECT COALESCE(SUM(diamonds),0) n FROM users").fetchone()["n"]
            pending = c.execute("SELECT COUNT(*) n FROM purchases WHERE status='pending'").fetchone()["n"]
            played = c.execute("SELECT COUNT(*) n FROM games WHERE status='finished'").fetchone()["n"]
        tax_total = bet_tax_total()
        text = ("╔══『 <b>📊 آمار و گزارش • 𝐕𝐈𝐏</b> 』══╗\n\n"
                f"👥 <b>کاربران:</b> {users:,}\n"
                f"💎 <b>مجموع الماس کاربران:</b> {total:,}\n"
                f"🧾 <b>رسیدهای در انتظار:</b> {pending:,}\n"
                f"🎮 <b>بازی‌های تکمیل‌شده:</b> {played:,}\n"
                f"🪙 <b>مالیات جمع‌شده:</b> {tax_total:,} الماس\n"
                f"🤖 <b>نرخ مالیات:</b> {BET_TAX_PERCENT}%\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "💠 <i>گزارش مالی سیستم NIRO SELF</i>\n"
                "╚═══════ <b>𝐕𝐈𝐏</b> ═══════╝")
        return await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_kb())
    if action == "settings":
        text = (f"⚙️ <b>تنظیمات ربات</b>\n\n"
                f"وضعیت ربات: {'روشن' if bot_is_enabled() else 'خاموش'}\n"
                f"گروه شرط‌بندی: {BET_GROUP_ID or 'تنظیم نشده'}\n"
                f"شماره کارت: {CARD_NUMBER}\n"
                "برای تغییر مقادیر، متغیرهای محیطی را ویرایش و ربات را راه‌اندازی مجدد کن.")
        return await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_kb())
    prompts = {
        "add":"آیدی عددی و مقدار را به شکل زیر بفرست:\n123456789 500",
        "sub":"آیدی عددی و مقدار کسر را بفرست:\n123456789 100",
        "block":"آیدی عددی کاربر را بفرست.",
        "unblock":"آیدی عددی کاربر را بفرست.",
        "message":"آیدی عددی، سپس متن را با | جدا کن:\n123456789 | متن پیام",
        "broadcast":"متن پیام همگانی را ارسال کن.",
        "gift":"مقدار الماس همگانی را ارسال کن.",
        "selfoff":"آیدی عددی کاربر را بفرست.",
        "selfon":"آیدی عددی کاربر را بفرست.",
        "off":"برای خاموش‌کردن ربات، عبارت تأیید خاموش را بفرست.",
        "on":"ربات روشن خواهد شد."
    }
    if action == "on":
        with db() as c: c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('bot_enabled','1')")
        return await q.edit_message_text("🟢 ربات روشن شد.", reply_markup=admin_kb())
    context.user_data["admin_action"] = action
    await q.edit_message_text("🛡 <b>عملیات مدیریت</b>\n\n" + prompts.get(action, "دستور را ارسال کن."),
                              parse_mode=ParseMode.HTML,
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]))

def bot_is_enabled():
    with db() as c:
        row = c.execute("SELECT value FROM settings WHERE key='bot_enabled'").fetchone()
    return not row or row["value"] == "1"

async def admin_back(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data.pop("admin_action", None)
    await q.edit_message_text("╔══『 🛡 پنل مدیریت • 𝐕𝐈𝐏 』══╗\n\n👑 ابزارهای مدیریتی و گزارش سیستم\n╚═══════ 𝐍𝐈𝐑𝐎 ═══════╝", reply_markup=admin_kb())

async def admin_text(update, context):
    action = context.user_data.get("admin_action")
    if not action or not is_admin(update.effective_user.id):
        return
    msg = update.message.text or ""
    context.user_data.pop("admin_action", None)
    try:
        if action in ("add", "sub"):
            uid_s, amount_s = msg.split()[:2]
            uid, amount = int(uid_s), int(amount_s)
            if not user_row(uid): return await update.message.reply_text("کاربر در ربات ثبت نشده است.")
            ok = change_balance(uid, amount if action == "add" else -amount,
                                "admin_add" if action == "add" else "admin_sub", "توسط ادمین")
            if not ok: return await update.message.reply_text("موجودی کاربر کافی نیست.")
            await update.message.reply_text("✅ موجودی با موفقیت تغییر کرد.")
            await context.bot.send_message(uid, f"💎 موجودی شما توسط مدیریت به‌روزرسانی شد.\nموجودی فعلی: {money_text(uid)}")
        elif action in ("block", "unblock"):
            uid = int(msg.strip())
            with db() as c: c.execute("UPDATE users SET blocked=? WHERE user_id=?", (1 if action=="block" else 0, uid))
            await update.message.reply_text("✅ انجام شد.")
        elif action == "message":
            a, text = msg.split("|", 1)
            await context.bot.send_message(int(a.strip()), text.strip())
            await update.message.reply_text("✅ پیام ارسال شد.")
        elif action == "broadcast":
            with db() as c: ids = [r["user_id"] for r in c.execute("SELECT user_id FROM users")]
            sent = 0
            for uid in ids:
                try: await context.bot.send_message(uid, msg); sent += 1
                except Exception: pass
            await update.message.reply_text(f"📣 پیام برای {sent} کاربر ارسال شد.")
        elif action == "gift":
            amount = int(msg)
            if amount <= 0: raise ValueError()
            with db() as c: ids = [r["user_id"] for r in c.execute("SELECT user_id FROM users")]
            for uid in ids:
                if uid != OWNER_ID: add_tx(uid, amount, "broadcast_gift", "هدیه همگانی")
            await update.message.reply_text(f"🎁 {amount:,} الماس به کاربران واجد شرایط اضافه شد.")
        elif action in ("selfoff", "selfon"):
            uid = int(msg)
            await update.message.reply_text("این نسخه بخش فعال‌سازی سلف را به‌صورت نمایشی نگه می‌دارد؛ اتصال به سلف واقعی هنوز پیاده‌سازی نشده است.")
        elif action == "off":
            if msg.strip() != "تأیید خاموش": return await update.message.reply_text("برای تأیید دقیقاً بنویس: تأیید خاموش")
            with db() as c: c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('bot_enabled','0')")
            await update.message.reply_text("🔴 ربات در حالت خاموش قرار گرفت. برای روشن‌کردن مجدد، /admin و گزینه روشن‌کردن را بزن.")
    except Exception as e:
        log.exception("admin operation")
        await update.message.reply_text("⚠️ اطلاعات نامعتبر است. قالب را بررسی کن.")

# ===================== گروه و بازی =====================
def group_game_keyboard(game_id):
    # Telegram doesn't offer true button background colors; emoji color accents emulate them.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 ورود / شرکت", callback_data=f"join:{game_id}"),
         InlineKeyboardButton("🔴 لغو شرط", callback_data=f"cancel:{game_id}")]
    ])

async def group_text(update, context):
    m = update.message
    if not m or not m.from_user:
        return
    register_user(m.from_user)
    txt = (m.text or "").strip()
    if txt == "موجودی":
        return await send_wallet(update, context, m.from_user)
    if m.chat.type == "private":
        return
    if txt in ("شرط‌ها", "چالش‌ها", "بازی‌های باز"):
        with db() as c:
            waiting = c.execute("SELECT id,creator_id,stake,created_at FROM games WHERE chat_id=? AND status='waiting' ORDER BY id DESC LIMIT 30", (m.chat_id,)).fetchall()
        if not waiting:
            return await m.reply_text("🟦 در حال حاضر هیچ چالش بازی منتظر بازیکن نیست.")
        lines = ["🎮 <b>چالش‌های باز این گروه</b>", "━━━━━━━━━━━━━━"]
        for game in waiting:
            row = user_row(game["creator_id"])
            name = (row["first_name"] if row else "بازیکن") or "بازیکن"
            lines.append(f"🟢 <b>#{game['id']}</b> | 💎 {game['stake']:,} | 👤 {name}")
        lines.append("\nبرای ورود به هر چالش، دکمه سبز زیر پیام همان چالش را بزن.")
        await m.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        return
    # ساخت چند چالش در یک پیام: «بازی 100 200 500» یا «بازی 100,200,500»
    mt = re.fullmatch(r"بازی\s+([0-9۰-۹٠-٩\s,،]+)", txt)
    if mt:
        raw_amounts = re.split(r"[\s,،]+", mt.group(1).strip())
        amounts = []
        for raw in raw_amounts:
            if not raw:
                continue
            raw = raw.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
            try:
                amounts.append(int(raw))
            except ValueError:
                return await m.reply_text("⚠️ مبلغ‌ها را فقط با عدد و جدا از هم وارد کن؛ مثال: بازی 100 200 500")
        if not amounts:
            return await m.reply_text("مبلغ شرط را وارد کن. مثال: بازی 100 200 500")
        if len(amounts) > 20:
            return await m.reply_text("⚠️ در هر پیام حداکثر ۲۰ چالش بساز.")
        if any(stake < 20 for stake in amounts):
            return await m.reply_text("⚠️ حداقل مبلغ هر چالش ۲۰ الماس است. همه مبلغ‌ها را بررسی کن.")
        uid = m.from_user.id
        b = balance(uid)
        if b is not None and any(stake > b for stake in amounts):
            return await m.reply_text("💎 موجودی شما برای حداقل یکی از مبلغ‌های انتخاب‌شده کافی نیست. مبلغ‌ها را کمتر کن.")
        # همه ردیف‌ها ساخته می‌شوند؛ هر چالش پیام و دکمه مستقل دارد.
        created = []
        for stake in amounts:
            with db() as c:
                cur = c.execute("INSERT INTO games(chat_id,message_id,creator_id,stake,created_at) VALUES(?,?,?,?,?)",
                               (m.chat_id, 0, uid, stake, datetime.utcnow().isoformat()))
                gid = cur.lastrowid
            # Minimal wager card only: no photo, no announcement/summary message.
            text = ("╔═══『 <b>𝐍𝐈𝐑𝐎 • 𝐕𝐈𝐏 𝐁𝐄𝐓</b> 』═══╗\n\n"
                    "💠 <b>چالش اختصاصی آماده است</b>\n"
                    f"💎 <b>مبلغ بازی:</b> <code>{stake:,}</code> الماس برای هر نفر\n"
                    f"🧾 <b>مالیات ربات:</b> {BET_TAX_PERCENT}% از مجموع شرط در صورت تکمیل بازی\n"
                    f"👑 <b>میزبان:</b> {m.from_user.mention_html()}\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "⚡ <i>برای ورود به رقابت، دکمه سبز را لمس کن.</i>\n"
                    "╚═══════ <b>𝐕𝐈𝐏</b> ═══════╝")
            creator_photo = await fetch_profile_bytes(context.bot, m.from_user.id)
            game_card = game_card_bytes(m.from_user, None, stake, creator_photo=creator_photo)
            sent = await m.reply_photo(photo=game_card, caption=text, parse_mode=ParseMode.HTML,
                                      reply_markup=group_game_keyboard(gid))
            with db() as c:
                c.execute("UPDATE games SET message_id=? WHERE id=?", (sent.message_id, gid))
            created.append((gid, stake))
        # Intentionally no extra summary message; each wager is its own button card.
        return
    if txt.startswith("انتقال "):
        if not m.reply_to_message or not m.reply_to_message.from_user:
            return await m.reply_text("برای انتقال، دستور «انتقال مقدار» را در پاسخ به پیام گیرنده بفرست.")
        try: amount = int(txt.split()[1])
        except Exception: return await m.reply_text("مقدار انتقال معتبر نیست.")
        target_user = m.reply_to_message.from_user
        target = target_user.id
        register_user(target_user)
        sender = m.from_user.id
        if amount <= 0 or target == sender or target == context.bot.id:
            return await m.reply_text("⚠️ مقدار یا گیرنده معتبر نیست.")
        if balance(sender) is not None and balance(sender) < amount:
            return await m.reply_text("💎 موجودی شما کافی نیست.")
        if sender != OWNER_ID:
            if not change_balance(sender, -amount, "transfer_out", f"به {target}"):
                return await m.reply_text("💎 موجودی شما کافی نیست.")
        add_tx(target, amount, "transfer_in", f"از {sender}")
        await m.reply_text(f"✅ انتقال انجام شد.\n💎 مقدار: {amount:,}\n👤 گیرنده: {m.reply_to_message.from_user.first_name}")
        try: await context.bot.send_message(target, f"🎁 شما {amount:,} الماس از طریق گروه دریافت کردید.")
        except Exception: pass

async def edit_game_message(q, text, **kwargs):
    if q.message and q.message.photo:
        return await q.edit_message_caption(caption=text, **kwargs)
    return await q.edit_message_text(text=text, **kwargs)


async def game_callbacks(update, context):
    q = update.callback_query
    data = q.data
    action, gid_s = data.split(":")
    gid = int(gid_s)
    uid = q.from_user.id
    with db() as c:
        g = c.execute("SELECT * FROM games WHERE id=?", (gid,)).fetchone()
    if not g or g["status"] != "waiting":
        return await q.answer("این بازی دیگر فعال نیست.", show_alert=True)
    if action == "cancel":
        if uid != g["creator_id"] and not is_admin(uid):
            return await q.answer("فقط سازنده بازی یا ادمین می‌تواند آن را لغو کند.", show_alert=True)
        with db() as c: c.execute("UPDATE games SET status='cancelled' WHERE id=?", (gid,))
        await q.answer("بازی لغو شد.")
        return await edit_game_message(q,
            "╔══『 🔴 <b>چالش لغو شد</b> 』══╗\n\n"
            "این رقابت توسط میزبان لغو گردید.\n"
            "💎 مبلغ شرط قفل نشده بود و بازی پایان یافت.\n\n"
            "╚════ <i>𝐍𝐈𝐑𝐎 𝐕𝐈𝐏</i> ════╝")
    if uid == g["creator_id"]:
        return await q.answer("برای پیوستن باید بازیکن دیگری وارد شود.", show_alert=True)
    if balance(uid) is not None and balance(uid) < g["stake"]:
        return await q.answer("موجودی الماس شما کافی نیست.", show_alert=True)
    # قفل اتمیک بازی و کسر شرط
    with db() as c:
        cur = c.execute("UPDATE games SET status='playing',opponent_id=? WHERE id=? AND status='waiting'",
                        (uid, gid))
        if cur.rowcount != 1:
            return await q.answer("بازیکن دیگری زودتر وارد شد.", show_alert=True)
    creator, opponent, stake = g["creator_id"], uid, g["stake"]
    if creator != OWNER_ID and not change_balance(creator, -stake, "bet_lock", f"بازی {gid}"):
        with db() as c: c.execute("UPDATE games SET status='waiting',opponent_id=NULL WHERE id=?", (gid,))
        return await q.answer("موجودی سازنده دیگر کافی نیست.", show_alert=True)
    if opponent != OWNER_ID and not change_balance(opponent, -stake, "bet_lock", f"بازی {gid}"):
        if creator != OWNER_ID: add_tx(creator, stake, "bet_refund", f"لغو بازی {gid}")
        with db() as c: c.execute("UPDATE games SET status='waiting',opponent_id=NULL WHERE id=?", (gid,))
        return await q.answer("موجودی شما کافی نیست.", show_alert=True)
    await q.answer("شرط‌ها ثبت شد؛ نتیجه در حال تعیین است.")
    start_caption = (
        "╔══『 ⚔️ <b>𝐕𝐈𝐏 𝐃𝐔𝐄𝐋 • آغاز رقابت</b> 』══╗\n\n"
        "🔒 <b>شرط هر دو بازیکن ثبت و قفل شد.</b>\n"
        f"💎 <b>مبلغ رقابت:</b> {stake:,} الماس برای هر نفر\n"
        f"🧾 <b>مالیات ربات:</b> {BET_TAX_PERCENT}% از مجموع شرط‌ها\n\n"
        "🎲 <i>سرنوشت این رقابت در حال مشخص‌شدن است…</i>\n"
        "╚══════ <b>𝐍𝐈𝐑𝐎 𝐕𝐈𝐏</b> ══════╝"
    )
    creator_user = await context.bot.get_chat(creator)
    opponent_user = await context.bot.get_chat(opponent)
    creator_photo = await fetch_profile_bytes(context.bot, creator)
    opponent_photo = await fetch_profile_bytes(context.bot, opponent)
    started_card = game_card_bytes(creator_user, opponent_user, stake, creator_photo=creator_photo, opponent_photo=opponent_photo)
    try:
        await q.message.edit_media(InputMediaPhoto(media=started_card, caption=start_caption, parse_mode=ParseMode.HTML), reply_markup=None)
    except Exception:
        # If Telegram refuses media replacement, retain the caption-based fallback.
        await edit_game_message(q, start_caption, parse_mode=ParseMode.HTML, reply_markup=None)
    try:
        # انتخاب تصادفی امن؛ هیچ تاس یا پیام اضافه‌ای در گروه ارسال نمی‌شود.
        winner = creator if secrets.randbelow(2) == 0 else opponent
        loser = opponent if winner == creator else creator
        gross_prize = stake * 2
        tax = (gross_prize * BET_TAX_PERCENT) // 100
        prize = gross_prize - tax
        record_bet_tax(tax, gid)
        if winner != OWNER_ID:
            add_tx(winner, prize, "bet_win", f"جایزه خالص شرط‌بندی بازی {gid} پس از مالیات {BET_TAX_PERCENT}%")
        with db() as c:
            c.execute("UPDATE games SET status='finished' WHERE id=? AND status='playing'", (gid,))
        winner_row = user_row(winner)
        winner_name = (winner_row['first_name'] if winner_row else None) or "بازیکن برنده"
        result = (
            "🏆 <b>قهرمان این رقابت:</b> "
            f"<a href='tg://user?id={winner}'>{winner_name}</a>\n"
            f"🥀 <b>بازنده:</b> <a href='tg://user?id={loser}'>مشاهده بازیکن</a>\n"
            "✨ <i>نتیجه با قرعه محرمانه مشخص شد.</i>"
        )
        await edit_game_message(
            q,
            "╔════════════════════╗\n"
            "   🏆 <b>𝐍𝐈𝐑𝐎 • 𝐕𝐈𝐏 𝐑𝐄𝐒𝐔𝐋𝐓</b>   \n"
            "╚════════════════════╝\n\n"
            f"🥊 <b>بازیکن اول:</b> <a href='tg://user?id={creator}'>نمایش پروفایل</a>\n"
            f"🥊 <b>بازیکن دوم:</b> <a href='tg://user?id={opponent}'>نمایش پروفایل</a>\n"
            f"💎 <b>شرط هر بازیکن:</b> {stake:,} الماس\n"
            f"🧾 <b>مالیات ربات ({BET_TAX_PERCENT}%):</b> {tax:,} الماس\n"
            f"💰 <b>جایزه خالص برنده:</b> {prize:,} الماس (از {gross_prize:,})\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"{result}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👑 <i>رقابت تمام شد؛ تبریک به قهرمان!</i>\n"
            "<b>𝐍𝐈𝐑𝐎 𝐕𝐈𝐏 • 𝐆𝐀𝐌𝐄 𝐂𝐄𝐍𝐓𝐄𝐑</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        log.exception("game error")
        if creator != OWNER_ID: add_tx(creator, stake, "bet_refund", f"خطای بازی {gid}")
        if opponent != OWNER_ID: add_tx(opponent, stake, "bet_refund", f"خطای بازی {gid}")
        with db() as c: c.execute("UPDATE games SET status='error' WHERE id=?", (gid,))
        await q.message.reply_text("⚠️ در اجرای بازی خطایی رخ داد؛ مبالغ شرط بازگردانده شد.")

# ===================== مسیریابی دکمه‌ها =====================
async def callbacks(update, context):
    data = update.callback_query.data
    if data == "wallet_details":
        await update.callback_query.answer(f"موجودی: {money_text(update.callback_query.from_user.id)}", show_alert=True)
        return
    if data == "home":
        await update.callback_query.answer()
        return await update.callback_query.edit_message_text(WELCOME, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())
    if data in ("account","self","group","config","free","help"):
        return await show_section(update, context)
    if data == "guide": return await guide(update, context)
    if data == "buy": return await buy_start(update, context)
    if data.startswith(("digit:","buy_confirm","buy_cancel")):
        return await buy_callbacks(update, context)
    if data.startswith("purchase:"): return await purchase_review(update, context)
    if data.startswith("adm:"): return await admin_callbacks(update, context)
    if data == "admin_back": return await admin_back(update, context)
    if data.startswith(("join:","cancel:")): return await game_callbacks(update, context)

async def gate(update, context):
    if not bot_is_enabled() and not is_admin(update.effective_user.id):
        if update.effective_chat.type == "private":
            await update.message.reply_text("⏸ ربات موقتاً توسط مدیریت خاموش شده است.")
        return
    if update.effective_chat.type == "private":
        if user_row(update.effective_user.id) and user_row(update.effective_user.id)["blocked"]:
            return
        if context.user_data.get("state") == "receipt":
            return await receipt_photo(update, context)
        if context.user_data.get("admin_action"):
            return await admin_text(update, context)
    return await group_text(update, context)

def main():
    if not BOT_TOKEN or BOT_TOKEN == "توکن_ربات_را_اینجا_بگذار":
        raise SystemExit("ابتدا BOT_TOKEN را در متغیرهای محیطی تنظیم کن.")
    init_db()
    upload_request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30,
        read_timeout=120,
        write_timeout=120,
        pool_timeout=30,
        media_write_timeout=180,
    )

    updates_request = HTTPXRequest(
        connection_pool_size=2,
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=30,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(upload_request)
        .get_updates_request(updates_request)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, gate))
    log.info("NIRO SELF started")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
