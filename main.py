from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yt_dlp

TOKEN = "8676327473:AAFLl25PE672P7BN1-5btVzEaCwU7_koGq0"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 نام آهنگ را بفرست")

async def music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text

    ydl_opts = {"quiet": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        video = info["entries"][0]

        await update.message.reply_text(
            f"🎧 {video['title']}\n{video['webpage_url']}"
        )

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, music))

print("Music Bot Running...")
app.run_polling()
