from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from rapidfuzz import fuzz

TOKEN = "8637704250:AAEQF3t_EzYZ8qvHub0AwTzNFbM4jsm5a5w"

# ذخیره پلی‌لیست
user_playlist = {}

# ----------------------------
# سرچ موزیک (API iTunes)
# ----------------------------
def search_songs(query):
    url = f"https://itunes.apple.com/search?term={query}&limit=5"
    res = requests.get(url).json()

    results = []

    for item in res.get("results", []):
        results.append({
            "title": item.get("trackName"),
            "artist": item.get("artistName"),
            "url": item.get("previewUrl")
        })

    return results

# ----------------------------
# /start
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎧 Music AI PRO Bot فعال شد\n\nاسم آهنگ رو بفرست 👇"
    )

# ----------------------------
# انتخاب آهنگ
# ----------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    title = data[1]
    artist = data[2]
    url = data[3]
    user_id = query.from_user.id

    user_playlist.setdefault(user_id, []).append(title)

    msg = f"""
🎵 {title}
👤 {artist}

🔗 Preview:
{url}
"""

    await query.message.reply_text(msg)

# ----------------------------
# پیام کاربر
# ----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    await update.message.reply_text("🔎 AI در حال جستجو...")

    songs = search_songs(text)

    if not songs:
        await update.message.reply_text("❌ چیزی پیدا نشد")
        return

    buttons = []

    for s in songs:
        score = fuzz.ratio(text.lower(), s["title"].lower())

        buttons.append([
            InlineKeyboardButton(
                f"🎵 {s['title'][:25]}",
                callback_data=f"song|{s['title']}|{s['artist']}|{s['url']}"
            )
        ])

    markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "🎧 نتایج:",
        reply_markup=markup
    )

# ----------------------------
# پلی‌لیست
# ----------------------------
async def playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    songs = user_playlist.get(user_id, [])

    if not songs:
        await update.message.reply_text("❌ پلی‌لیست خالی است")
        return

    await update.message.reply_text(
        "🎶 پلی‌لیست شما:\n\n" + "\n".join(songs[-10:])
    )

# ----------------------------
# اجرا
# ----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("playlist", playlist))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

print("🎧 Music AI PRO Bot Running...")
app.run_polling()
