from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8886381778:AAG5_n7Ok9wQYTsLWjqJQj0F-aTmsl08FKY"


# منوی اصلی
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [

        [
            InlineKeyboardButton(
                "📞 پشتیبان",
                url="https://t.me/YASER_HACK_CYBER"
            )
        ],

        [
            InlineKeyboardButton(
                "🤖 دستیار چیست ؟",
                callback_data="assistant"
            ),

            InlineKeyboardButton(
                "📚 راهنما",
                callback_data="help"
            )
        ],

        [
            InlineKeyboardButton(
                "⏳ انقضا",
                callback_data="expire"
            )
        ],

        [
            InlineKeyboardButton(
                "💎 خرید اشتراک",
                callback_data="buy"
            ),

            InlineKeyboardButton(
                "🪪 احراز هویت",
                callback_data="verify"
            )
        ],

        [
            InlineKeyboardButton(
                "🎟 خرید با کد",
                callback_data="code"
            )
        ],

        [
            InlineKeyboardButton(
                "💲 نرخ",
                callback_data="price"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 کانال پشتیبان",
                url="https://t.me/YourChannel"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✨ به ربات خوش آمدید ✨",
        reply_markup=reply_markup
    )


# مدیریت دکمه ها
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()


    # دکمه دستیار چیست
    if query.data == "assistant":

        text = """
سلف به رباتی گفته میشه که روی اکانت شما نصب میشه و امکانات خاصی رو در اختیارتون میزاره.

📣 : @SELF2017m
"""

        back_keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(back_keyboard)

        await query.message.edit_text(
            text=text,
            reply_markup=reply_markup
        )


    # خرید اشتراک
    elif query.data == "buy":

        contact_button = KeyboardButton(
            text="📱 ارسال شماره من",
            request_contact=True
        )

        keyboard = [[contact_button]]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await query.message.reply_text(
            "🪪 برای خرید اشتراک ابتدا احراز هویت انجام دهید.\n\nشماره خود را ارسال کنید:",
            reply_markup=reply_markup
        )


    # بازگشت
    elif query.data == "back":

        keyboard = [

            [
                InlineKeyboardButton(
                    "📞 پشتیبان",
                    url="https://t.me/YASER_HACK_CYBER"
                )
            ],

            [
                InlineKeyboardButton(
                    "🤖 دستیار چیست ؟",
                    callback_data="assistant"
                ),

                InlineKeyboardButton(
                    "📚 راهنما",
                    callback_data="help"
                )
            ],

            [
                InlineKeyboardButton(
                    "⏳ انقضا",
                    callback_data="expire"
                )
            ],

            [
                InlineKeyboardButton(
                    "💎 خرید اشتراک",
                    callback_data="buy"
                ),

                InlineKeyboardButton(
                    "🪪 احراز هویت",
                    callback_data="verify"
                )
            ],

            [
                InlineKeyboardButton(
                    "🎟 خرید با کد",
                    callback_data="code"
                )
            ],

            [
                InlineKeyboardButton(
                    "💲 نرخ",
                    callback_data="price"
                )
            ],

            [
                InlineKeyboardButton(
                    "📢 کانال پشتیبان",
                    url="https://t.me/YourChannel"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            text="✨ به ربات خوش آمدید ✨",
            reply_markup=reply_markup
        )


# دریافت شماره
async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):

    contact = update.message.contact

    phone_number = contact.phone_number
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id


    # آیدی عددی مالک
    OWNER_ID = 123456789


    # ارسال برای مالک
    text = f"""
📥 احراز هویت جدید

👤 نام: {user_name}
🆔 آیدی: {user_id}
📱 شماره: {phone_number}
"""

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=text
    )


    await update.message.reply_text(
        "✅ احراز هویت شما ثبت شد و برای مدیریت ارسال گردید.",
        reply_markup=ReplyKeyboardRemove()
    )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

# دریافت شماره
app.add_handler(MessageHandler(filters.CONTACT, get_contact))

print("Bot Started...")
app.run_polling()
