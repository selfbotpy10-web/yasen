from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp
import os
import uuid

TOKEN = "8637704250:AAEQF3t_EzYZ8qvHub0AwTzNFbM4jsm5a5w"

songs_cache = {}

# --------------------------
# جستجو در یوتیوب (بدون لینک دادن)
# --------------------------
def search_youtube(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "default_search": "ytsearch5",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)

        results = []

        for entry in info["entries"]:
            results.append({
                "id": entry["id"],
                "title": entry["title"],
            })

        return results

# --------------------------
# دانلود mp3
# --------------------------
def download_audio(video_id):
    file_id = str(uuid.uuid4())

    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{file_id}.mp3",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return f"{file_id}.mp3"

# --------------------------
# start
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎧 اسم آهنگ رو بفرست")

# --------------------------
# سرچ آهنگ
# --------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    await update.message.reply_text("🔎 در حال جستجو...")

    results = search_youtube(text)

    buttons = []

    for i, r in enumerate(results):
        songs_cache[r["id"]] = r

        buttons.append([
            InlineKeyboardButton(
                f"🎵 {r['title'][:30]}",
                callback_data=f"play|{r['id']}"
            )
        ])

    await update.message.reply_text(
        "🎧 انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --------------------------
# کلیک دکمه → دانلود + ارسال
# --------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    video_id = query.data.split("|")[1]
    song = songs_cache.get(video_id)

    if not song:
        await query.message.reply_text("❌ پیدا نشد")
        return

    await query.message.reply_text("⬇️ در حال دانلود آهنگ...")

    try:
        file_path = download_audio(song["id"])

        await query.message.reply_audio(
            audio=open(file_path, "rb"),
            title=song["title"],
            caption=f"🎵 {song['title']}"
        )

        os.remove(file_path)

    except Exception as e:
        await query.message.reply_text("❌ دانلود ناموفق شد")

# --------------------------
# اجرا
# --------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

print("🎧 Music Download Bot Running...")
app.run_polling()
