import os
import re
import sqlite3
import logging
import asyncio
import secrets
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from dotenv import load_dotenv

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
DB_PATH = os.getenv("DB_PATH", "niro_self.sqlite3")
GAME_IMAGE_PATH = os.getenv("GAME_IMAGE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_start.png"))

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

# ===================== متن‌ها و منو =====================
WELCOME = (
    "✨ <b>به NIRO SELF خوش آمدی!</b>\n\n"
    "اینجا مرکز مدیریت امکانات، حساب کاربری و خدمات ربات نایرو است.\n"
    "💎 موجودی الماس خود را مدیریت کن.\n"
    "🛡️ از بخش‌های اختصاصی و ابزارهای ربات استفاده کن.\n"
    "🎮 در گروه‌های مجاز با دوستانت بازی کن.\n"
    "🎁 با دعوت دوستان، الماس هدیه بگیر.\n"
    "📨 برای راهنمایی و پشتیبانی همیشه می‌توانی پیام بدهی.\n"
    "🚀 از منوی زیر، بخش موردنظرت را انتخاب کن."
)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ فعال‌سازی سلف", callback_data="self")],
        [InlineKeyboardButton("👥 مدیریت گروه و بازی", callback_data="group"),
         InlineKeyboardButton("👤 حساب کاربری", callback_data="account")],
        [InlineKeyboardButton("💎 خرید الماس", callback_data="buy"),
         InlineKeyboardButton("🎁 الماس رایگان", callback_data="free")],
        [InlineKeyboardButton("🧾 کانفیگ", callback_data="config"),
         InlineKeyboardButton("📚 راهنما و پشتیبانی", callback_data="help")]
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
        "👤 <b>حساب کاربری NIRO SELF</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"🪪 شناسه عددی: <code>{u.id}</code>\n"
        f"🌐 نام کاربری: @{u.username or 'ندارد'}\n"
        f"💎 موجودی الماس: <b>{money_text(u.id)}</b>\n"
        f"📅 عضویت: {row['created_at'][:10] if row and row['created_at'] else '—'}\n"
        "🔐 وضعیت حساب: فعال\n"
        "📊 موجودی شما در سیستم مرکزی ثبت و نگهداری می‌شود.\n"
        "🎁 با دعوت دوستان می‌توانی الماس بیشتری دریافت کنی.\n"
        "━━━━━━━━━━━━━━\n"
        "✨ ممنون که NIRO SELF را انتخاب کردی."
    )
    await q.edit_message_text(text, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]))

async def show_section(update, context):
    q = update.callback_query
    await q.answer()
    key = q.data
    if key == "account":
        return await account(update, context)
    if key == "self":
        text = (
            "🛠 <b>پنل NIRO SELF</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "یکی از امکانات پنل را انتخاب کن:\n"
            "🔐 حساب شخصی خودت را فقط روی دستگاه خودت مدیریت کن."
        )
        kb = [
            [InlineKeyboardButton("🕒 ساعت بیو", callback_data="selfinfo:bio"),
             InlineKeyboardButton("🕒 ساعت نام خانوادگی", callback_data="selfinfo:surname")],
            [InlineKeyboardButton("💬 پاسخ خودکار", callback_data="selfinfo:reply"),
             InlineKeyboardButton("👥 دوستان و دشمنان", callback_data="selfinfo:friends")],
            [InlineKeyboardButton("💾 ذخیره رسانه", callback_data="selfinfo:media"),
             InlineKeyboardButton("⚙️ تنظیمات", callback_data="selfinfo:settings")],
            [InlineKeyboardButton("📖 راهنمای اتصال", callback_data="guide")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
        ]
    elif key == "config":
        text = "⚙️ <b>بخش کانفیگ</b>\n\nاین خدمت در حال آماده‌سازی است و به‌زودی در NIRO SELF فعال می‌شود."
        kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    elif key == "group":
        text = ("🎮 <b>مرکز مدیریت گروه و بازی NIRO</b>\n\n"
                "برای استفاده از بازی و انتقال الماس، ربات را در گروه موردنظر ادمین کن.\n"
                "در گروه می‌توانی از دستورهای «بازی ۲۰»، «موجودی» و «انتقال ۲۰» استفاده کنی.")
        kb = [[InlineKeyboardButton("🔗 ورود به گروه شرط‌بندی", url=BET_GROUP_LINK)],
              [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    elif key == "free":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={q.from_user.id}"
        text = ("🎁 <b>باشگاه دعوت NIRO SELF</b>\n\n"
                "با دعوت دوستانت به خانواده نایرو، الماس هدیه بگیر!\n"
                "💎 به‌ازای هر کاربر جدید و یکتا که با لینک تو وارد شود: <b>۵۰ الماس</b>\n"
                "🔒 هر شخص فقط یک‌بار می‌تواند پاداش دعوت ایجاد کند.\n\n"
                f"🔗 لینک اختصاصی تو:\n<code>{link}</code>\n\n"
                "لینک را برای دوستانت ارسال کن و هدیه‌ات را دریافت کن.")
        kb = [[InlineKeyboardButton("📤 اشتراک‌گذاری لینک", url=f"https://t.me/share/url?url={link}")],
              [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    elif key == "help":
        text = "📚 <b>راهنما و پشتیبانی</b>\n\nیکی از گزینه‌های زیر را انتخاب کن."
        kb = [[InlineKeyboardButton("📖 راهنمای فعال‌سازی سلف", callback_data="guide")],
              [InlineKeyboardButton("🎧 ارتباط با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
              [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]
    else:
        return
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def self_feature_info(update, context):
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]

    pages = {
        "bio": ("🕒 ساعت بیو", "نمایش ساعت در بیوگرافی حساب. فعال‌سازی و تنظیم آن باید روی حساب شخصی خودت انجام شود."),
        "surname": ("🕒 ساعت نام خانوادگی", "تغییر زمان‌دار نام خانوادگی. برای جلوگیری از تغییر ناخواسته، این تنظیم فقط روی حسابی که خودت کنترل می‌کنی انجام شود."),
        "reply": ("💬 پاسخ خودکار", "تنظیم متن پاسخ خودکار، زمان فعالیت و محدودکردن پاسخ به مخاطبین."),
        "friends": ("👥 دوستان و دشمنان", "تنظیم فهرست مخاطبین مجاز و فهرست‌هایی که پاسخ خودکار برایشان فعال یا غیرفعال باشد."),
        "media": ("💾 ذخیره رسانه", "مدیریت ذخیره رسانه‌هایی که خودت مجاز به دریافت و نگهداری آن‌ها هستی."),
        "settings": ("⚙️ تنظیمات", "تنظیمات پنل و راهنمای اجرای محلی. اطلاعات ورود و فایل سشن را در اختیار ربات یا افراد دیگر قرار نده."),
    }

    title, description = pages.get(key, ("پنل NIRO", "گزینه نامعتبر است."))
    text = f"<b>{title}</b>\\n━━━━━━━━━━━━━━\\n\\n{description}\\n\\n🛡️ این صفحه تنظیمات را نمایش می‌دهد؛ اجرای واقعی روی حساب باید در دستگاه و حساب خودت انجام شود."
    kb = [
        [InlineKeyboardButton("⬅️ برگشت به پنل", callback_data="self")],
        [InlineKeyboardButton("📖 راهنما", callback_data="guide")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")]
    ]
    await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))


async def guide(update, context):
    q = update.callback_query
    await q.answer()
    text = (
        "📖 <b>راهنمای اتصال NIRO SELF</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        "۱️⃣ از حساب تلگرام خودت و دستگاه شخصی‌ات استفاده کن.\n\n"
        "۲️⃣ کد ورود تلگرام و رمز دوم را فقط در برنامه رسمی تلگرام وارد کن.\n\n"
        "۳️⃣ سشن یا فایل ورود حساب را برای افراد دیگر ارسال نکن.\n\n"
        "۴️⃣ برای مدیریت حساب، از تنظیمات تلگرام و دستگاه‌های متصل استفاده کن.\n\n"
        "🛡️ NIRO هیچ کد ورود یا رمز دوم تو را درخواست نمی‌کند."
    )
    await q.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛠️ پنل سلف", callback_data="self")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="help")]
        ])
    )

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
        "💎 <b>درگاه خرید الماس NIRO</b>\n\n"
        "مقدار دلخواه الماس را با صفحه‌کلید زیر وارد کن.\n"
        "پس از بررسی مقدار، اطلاعات پرداخت نمایش داده می‌شود.",
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
        text = (f"💳 <b>اطلاعات پرداخت</b>\n\n"
                f"💎 مقدار سفارش: <b>{amount:,} الماس</b>\n"
                f"🏦 شماره کارت: <code>{CARD_NUMBER}</code>\n"
                f"👤 به نام: <b>{CARD_OWNER}</b>\n\n"
                "پس از پرداخت، تصویر واضح رسید را همین‌جا ارسال کن.\n"
                "⚠️ تا زمان تأیید ادمین، الماس به حساب اضافه نمی‌شود.")
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
        [InlineKeyboardButton("📊 آمار ربات", callback_data="adm:stats"),
         InlineKeyboardButton("⚙️ تنظیمات", callback_data="adm:settings")],
        [InlineKeyboardButton("➕ افزایش موجودی", callback_data="adm:add"),
         InlineKeyboardButton("➖ کسر موجودی", callback_data="adm:sub")],
        [InlineKeyboardButton("📣 پیام همگانی", callback_data="adm:broadcast"),
         InlineKeyboardButton("💎 موجودی همگانی", callback_data="adm:gift")],
        [InlineKeyboardButton("✉️ پیام به کاربر", callback_data="adm:message")],
        [InlineKeyboardButton("🚫 بلاک کاربر", callback_data="adm:block"),
         InlineKeyboardButton("🔓 آنبلاک کاربر", callback_data="adm:unblock")],
        [InlineKeyboardButton("🔴 خاموش‌کردن سلف", callback_data="adm:selfoff"),
         InlineKeyboardButton("🟢 روشن‌کردن سلف", callback_data="adm:selfon")],
        [InlineKeyboardButton("⏸ خاموش‌کردن ربات", callback_data="adm:off"),
         InlineKeyboardButton("▶️ روشن‌کردن ربات", callback_data="adm:on")],
        [InlineKeyboardButton("🔙 بازگشت به پنل ربات", callback_data="home")]
    ])

async def admin_command(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ دسترسی غیرمجاز.")
    with db() as c:
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('bot_enabled','1')")
    await update.message.reply_text("🛡 <b>پنل مدیریت NIRO SELF</b>\n\nاز گزینه‌های زیر استفاده کن.",
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
        text = f"📊 <b>آمار NIRO SELF</b>\n\n👥 کاربران: {users:,}\n💎 مجموع الماس کاربران: {total:,}\n🧾 رسیدهای در انتظار: {pending:,}"
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
    await q.edit_message_text("🛡 پنل مدیریت NIRO SELF", reply_markup=admin_kb())

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
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎲 پیوستن به بازی", callback_data=f"join:{game_id}"),
        InlineKeyboardButton("❌ لغو بازی", callback_data=f"cancel:{game_id}")
    ]])

async def group_text(update, context):
    m = update.message
    if not m or m.chat.type == "private" or not m.from_user:
        return
    register_user(m.from_user)
    txt = (m.text or "").strip()
    if txt == "موجودی":
        await m.reply_text(f"👤 {m.from_user.first_name}\n💎 موجودی: {money_text(m.from_user.id)}")
        return
    mt = re.fullmatch(r"بازی\s+(\d+)", txt)
    if mt:
        stake = int(mt.group(1))
        if stake < 20:
            return await m.reply_text("⚠️ حداقل مبلغ بازی ۲۰ الماس است.")
        uid = m.from_user.id
        b = balance(uid)
        if b is not None and b < stake:
            return await m.reply_text("💎 موجودی شما برای ایجاد این بازی کافی نیست.")
        with db() as c:
            active = c.execute("SELECT id FROM games WHERE chat_id=? AND status='waiting'", (m.chat_id,)).fetchone()
            if active: return await m.reply_text("⏳ در این گروه یک بازی در انتظار بازیکن است.")
            cur = c.execute("INSERT INTO games(chat_id,message_id,creator_id,stake,created_at) VALUES(?,?,?,?,?)",
                            (m.chat_id, 0, uid, stake, datetime.utcnow().isoformat()))
            gid = cur.lastrowid
        text = (f"🎮 <b>چالش NIRO آغاز شد!</b>\n\n"
                f"👤 سازنده: {m.from_user.mention_html()}\n"
                f"💎 مبلغ شرط هر نفر: <b>{stake:,} الماس</b>\n"
                "🤝 بازیکن دوم برای ورود، دکمه پیوستن را بزند.\n"
                "🔒 پس از پیوستن، مبلغ بازی قفل و نتیجه مخفیانه تعیین می‌شود.")
        try:
            with open(GAME_IMAGE_PATH, "rb") as photo:
                sent = await m.reply_photo(
                    photo=photo,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=group_game_keyboard(gid)
                )
        except Exception:
            log.exception("ارسال عکس شروع بازی ناموفق بود")
            sent = await m.reply_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=group_game_keyboard(gid)
            )
        with db() as c: c.execute("UPDATE games SET message_id=? WHERE id=?", (sent.message_id, gid))
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
        return await edit_game_message(q, "❌ این چالش توسط سازنده لغو شد.")
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
    await edit_game_message(
        q,
        "🔐 <b>شرط‌بندی مخفی NIRO شروع شد!</b>\n\n"
        "💎 مبلغ شرط هر بازیکن قفل شد.\n"
        "🎯 نتیجه بدون نمایش تاس و به‌صورت تصادفی تعیین می‌شود...",
        parse_mode=ParseMode.HTML
    )
    try:
        # انتخاب تصادفی امن؛ هیچ تاس یا پیام اضافه‌ای در گروه ارسال نمی‌شود.
        winner = creator if secrets.randbelow(2) == 0 else opponent
        loser = opponent if winner == creator else creator
        prize = stake * 2
        if winner != OWNER_ID:
            add_tx(winner, prize, "bet_win", f"برد شرط‌بندی مخفی بازی {gid}")
        with db() as c:
            c.execute("UPDATE games SET status='finished' WHERE id=? AND status='playing'", (gid,))
        winner_row = user_row(winner)
        winner_name = (winner_row['first_name'] if winner_row else None) or "بازیکن برنده"
        result = (
            "🏆 <b>برنده این دور:</b> "
            f"<a href='tg://user?id={winner}'>{winner_name}</a>\n"
            f"💎 <b>جایزه:</b> {prize:,} الماس\n"
            f"📉 بازنده: <a href='tg://user?id={loser}'>مشاهده بازیکن</a>\n"
            "🔒 نتیجه مخفیانه تعیین شد و تاس نمایش داده نشد."
        )
        await edit_game_message(
            q,
            "🎮 <b>نتیجه نهایی شرط‌بندی NIRO</b>\n\n"
            f"👤 بازیکن اول: <a href='tg://user?id={creator}'>مشاهده</a>\n"
            f"👤 بازیکن دوم: <a href='tg://user?id={opponent}'>مشاهده</a>\n"
            f"💰 مبلغ شرط هر نفر: <b>{stake:,} الماس</b>\n\n"
            f"{result}\n\n"
            "✨ این پیام نتیجه نهایی بازی است.",
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
    if data == "home":
        await update.callback_query.answer()
        return await update.callback_query.edit_message_text(WELCOME, parse_mode=ParseMode.HTML, reply_markup=main_keyboard())
    if data in ("account","self","group","config","free","help"):
        return await show_section(update, context)
    if data.startswith("selfinfo:"):
        return await self_feature_info(update, context)
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
