from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

import requests

TOKEN = "8637704250:AAEQF3t_EzYZ8qvHub0AwTzNFbM4jsm5a5w"

# ذخیره موقت آهنگ‌ها
songs_cache = {}

# ----------------------------
# جستجوی موزیک (iTunes API)
# ----------------------------
def search_songs(query):
    url = f"https://itunes.apple.com/search?term={query}&limit=5"
    res = requests.get(url).json()

    results = []
    for item in res.get("results", []):
        results.append({
            "title": item.get("trackName", "Unknown"),
            "artist": item.get("artistName", "Unknown"),
            "url": item.get("previewUrl", "No link")
        })

    return results

# ----------------------------
# /start
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎧 Music AI Bot فعال شد\n\nاسم آهنگ رو بفرست 👇"
    )

# ----------------------------
# دریافت پیام کاربر
# ----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    await update.message.reply_text("🔎 در حال جستجو...")

    songs = search_songs(text)

    if not songs:
        await update.message.reply_text("❌ چیزی پیدا نشد")
        return

    buttons = []

    for i, s in enumerate(songs):
        song_id = str(len(songs_cache) + i)
        songs_cache[song_id] = s

        buttons.append([
            InlineKeyboardButton(
                f"🎵 {s['title'][:25]}",
                callback_data=f"song|{song_id}"
            )
        ])

    markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "🎧 نتایج:",
        reply_markup=markup
    )

# ----------------------------
# کلیک روی دکمه
# ----------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        song_id = query.data.split("|")[1]
        song = songs_cache.get(song_id)

        if not song:
            await query.message.reply_text("❌ آهنگ پیدا نشد")
            return

        msg = (
            f"🎵 Title: {song['title']}\n"
            f"👤 Artist: {song['artist']}\n\n"
            f"🔗 Preview:\n{song['url']}"
        )

        await query.message.reply_text(msg)

    except Exception:
        await query.message.reply_text("❌ خطا در پردازش")

# ----------------------------
# اجرا
# ----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

print("🎧 Bot Running...")
app.run_polling()
