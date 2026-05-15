from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp
import asyncio
import threading
import os

# =========================
# توکن ربات مادر
# =========================
MAIN_BOT_TOKEN = "8819363353:AAG1BYGdVnd4mgHzQk0rYGCmeOh5THclx88"

# =========================
# زبان‌ها
# =========================
languages = [
    "🇮🇷 فارسی",
    "🇬🇧 English",
    "🇮🇳 Hindi",
    "🇹🇷 Turkish",
    "🇸🇦 Arabic",
    "🇫🇷 French",
    "🇩🇪 German",
    "🇪🇸 Spanish",
    "🇷🇺 Russian",
    "🇮🇹 Italian"
]

# کیبورد زبان‌ها
lang_keyboard = ReplyKeyboardMarkup(
    [[lang] for lang in languages],
    resize_keyboard=True
)

# کیبورد ساخت ربات
bot_keyboard = ReplyKeyboardMarkup(
    [["🤖 ساخت ربات"]],
    resize_keyboard=True
)

# ذخیره کاربران
users = {}

# جلوگیری از اجرای تکراری ربات فرزند
running_bots = {}

# =====================================================
# بخش ربات فرزند (موزیک یاب)
# =====================================================

async def child_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 ربات موزیک یاب فعال شد\n\n"
        "نام آهنگ مورد نظر را ارسال کن:"
    )

async def child_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text

    await update.message.reply_text(
        "🔎 در حال جستجو و دانلود آهنگ ..."
    )

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch1",
        "outtmpl": "%(title)s.%(ext)s",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)

            if "entries" in info:
                info = info["entries"][0]

            title = info["title"]
            file_path = ydl.prepare_filename(info)

            await update.message.reply_audio(
                audio=open(file_path, "rb"),
                title=title,
                caption=f"🎧 {title}"
            )

            await update.message.reply_text(
                "✅ آهنگ با موفقیت ارسال شد"
            )

            # حذف فایل بعد از ارسال
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as e:
        await update.message.reply_text(
            f"درهال دانلود موزیک صبور باشید\n\n{str(e)}"
        )

def run_child_bot(token):
    async def start_bot():
        app = ApplicationBuilder().token(token).build()

        app.add_handler(CommandHandler("start", child_start))
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                child_music
            )
        )

        print(f"Child Bot Running: {token}")

        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        while True:
            await asyncio.sleep(999999)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

def start_child_bot(token):
    if token in running_bots:
        return

    t = threading.Thread(
        target=run_child_bot,
        args=(token,),
        daemon=True
    )
    t.start()

    running_bots[token] = True


# =====================================================
# بخش ربات مادر (ربات‌ساز)
# =====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 زبان مورد نظر خود را انتخاب کنید:",
        reply_markup=lang_keyboard
    )

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # انتخاب زبان
    if text in languages:
        users[user_id] = {
            "step": "language_selected"
        }

        await update.message.reply_text(
            "✅ زبان انتخاب شد\n\n"
            "حالا روی دکمه ساخت ربات بزن:",
            reply_markup=bot_keyboard
        )
        return

    # کلیک روی ساخت ربات
    if text == "🤖 ساخت ربات":
        if user_id not in users:
            await update.message.reply_text(
                "اول زبان خود را انتخاب کن",
                reply_markup=lang_keyboard
            )
            return

        users[user_id]["step"] = "waiting_token"

        await update.message.reply_text(
            "🔑 توکن ربات را ارسال کن:"
        )
        return

    # دریافت توکن ربات فرزند
    if (
        user_id in users
        and users[user_id].get("step") == "waiting_token"
    ):
        child_token = text

        try:
            start_child_bot(child_token)

            users[user_id]["step"] = "done"

            await update.message.reply_text(
                "✅ ربات فرزند با موفقیت فعال شد!\n\n"
                "حالا برو داخل همان ربات فرزند و /start بزن\n\n"
                "🎵 از این به بعد ربات موزیک یاب روی همان ربات فعال است."
            )

        except Exception:
            await update.message.reply_text(
                "❌ توکن نامعتبر است"
            )

        return


# =====================================================
# اجرای ربات مادر
# =====================================================

app = ApplicationBuilder().token(MAIN_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handler
    )
)

print("Main Bot Running ✅")
app.run_polling()
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import yt_dlp
import asyncio
import threading
import os

MAIN_BOT_TOKEN = "توکن_اینجا"

os.environ["NO_PROXY"] = "*"

users = {}
running_bots = {}

# =========================
# ذخیره پلی‌لیست ساده
# =========================
user_history = {}

# =========================
# ربات فرزند
# =========================

async def child_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 ربات موزیک فعال شد\n\nاسم آهنگ را بفرست 🎧"
    )


async def download_music(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch1",
        "outtmpl": "music.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=True)

        video = info["entries"][0]
        title = video["title"]

        return title, "music.mp3"


async def child_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.message.text

    await update.message.reply_text("🔎 در حال دانلود آهنگ...")

    try:
        title, file_path = await asyncio.to_thread(download_music, query)

        # ذخیره پلی‌لیست
        user_history.setdefault(user_id, []).append(title)

        await update.message.reply_audio(
            audio=open(file_path, "rb"),
            title=title,
            caption=f"🎧 {title}"
        )

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await update.message.reply_text("❌ خطا در دانلود")


def run_child(token):
    async def start():
        app = ApplicationBuilder().token(token).build()

        app.add_handler(CommandHandler("start", child_start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, child_music))

        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        while True:
            await asyncio.sleep(999999)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start())


def start_child_bot(token):
    if token in running_bots:
        return

    threading.Thread(target=run_child, args=(token,), daemon=True).start()
    running_bots[token] = True


# =========================
# ربات مادر
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 سلام!\n\n"
        "برای ساخت ربات توکن را بفرست\n"
        "یا اسم آهنگ را تایپ کن 🎵"
    )


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # ساخت ربات
    if "bot" in text.lower() and ":" in text:
        start_child_bot(text)
        await update.message.reply_text("✅ ربات ساخته شد 🎵")
        return

    # پلی‌لیست
    if user_id in user_history:
        history = user_history[user_id]
        if "playlist" in text.lower():
            await update.message.reply_text(
                "🎶 پلی‌لیست شما:\n\n" + "\n".join(history[-10:])
            )
            return

    # سرچ آهنگ
    try:
        await child_music(update, context)
    except:
        await update.message.reply_text("❌ خطا")


# =========================
# اجرا
# =========================

app = ApplicationBuilder().token(MAIN_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("🚀 Pro Music Bot Running...")
app.run_polling()
