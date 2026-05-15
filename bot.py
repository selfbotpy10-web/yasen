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
import os

# =========================
# توکن ربات اصلی
# =========================
MAIN_BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

# =========================
# ذخیره کاربران
# =========================
users = {}

# =========================
# دانلود موزیک
# =========================
def download_music(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch1",
        "outtmpl": "music.%(ext)s",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)

        if "entries" in info:
            info = info["entries"][0]

        title = info["title"]
        file_path = ydl.prepare_filename(info)

        return title, file_path


# =========================
# /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 سلام!\n\nاسم آهنگ را بفرست تا دانلود کنم"
    )


# =========================
# پیام کاربر
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text

    await update.message.reply_text("🔎 در حال دانلود...")

    try:
        title, file_path = await asyncio.to_thread(download_music, query)

        await update.message.reply_audio(
            audio=open(file_path, "rb"),
            title=title,
            caption=f"🎧 {title}"
        )

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{e}")


# =========================
# اجرای ربات
# =========================
app = ApplicationBuilder().token(MAIN_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()
