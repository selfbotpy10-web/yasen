from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests

TOKEN = "8637704250:AAEQF3t_EzYZ8qvHub0AwTzNFbM4jsm5a5w"

songs_cache = {}

# -------------------------
# سرچ موزیک
# -------------------------
def search_songs(query):
    url = f"https://itunes.apple.com/search?term={query}&limit=10"
    res = requests.get(url).json()

    results = []

    for item in res.get("results", []):
        title = item.get("trackName")
        artist = item.get("artistName")
        preview = item.get("previewUrl")

        # ❌ حذف آهنگ‌های بدون لینک
        if not preview:
            continue

        results.append({
            "title": title,
            "artist": artist,
            "url": preview
        })

    return results

# -------------------------
# start
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎧 آهنگ بفرست")

# -------------------------
# پیام کاربر
# -------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    await update.message.reply_text("🔎 در حال جستجو...")

    songs = search_songs(text)

    if not songs:
        await update.message.reply_text("❌ چیزی پیدا نشد")
        return

    buttons = []

    for i, s in enumerate(songs):
        song_id = f"{update.effective_user.id}_{i}"
        songs_cache[song_id] = s

        buttons.append([
            InlineKeyboardButton(
                f"🎵 {s['title'][:25]}",
                callback_data=f"song|{song_id}"
            )
        ])

    await update.message.reply_text(
        "🎧 نتایج:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# -------------------------
# کلیک دکمه
# -------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        song_id = query.data.split("|")[1]
        song = songs_cache.get(song_id)

        if not song:
            await query.message.reply_text("❌ آهنگ پیدا نشد")
            return

        await query.message.reply_text(
            f"🎵 {song['title']}\n"
            f"👤 {song['artist']}\n\n"
            f"🔗 {song['url']}"
        )

    except Exception:
        await query.message.reply_text("❌ خطا در اجرای دکمه")

# -------------------------
# اجرا
# -------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

print("🎧 Bot Running...")
app.run_polling()
