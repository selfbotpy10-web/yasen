from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp
import asyncio
import os

TOKEN = "8886381778:AAG5_n7Ok9wQYTsLWjqJQj0F-aTmsl08FKY"

def download_audio(query):
    ydl_opts = {
        "format": "bestaudio",
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
        file = ydl.prepare_filename(info)
        return title, file

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 اسم آهنگ رو بفرست")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 در حال دانلود...")

    try:
        title, file = await asyncio.to_thread(download_audio, update.message.text)

        await update.message.reply_audio(
            audio=open(file, "rb"),
            title=title
        )

        os.remove(file)

    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot Running...")
app.run_polling()
