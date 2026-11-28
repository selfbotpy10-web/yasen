from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"خطا: بخش «{label}» دقیقاً یک بار پیدا نشد. هیچ تغییری ذخیره نشد.")
    s = s.replace(old, new, 1)
    print("انجام شد:", label)

# مسیر عکس
replace_once(
    'DB_PATH = os.getenv("DB_PATH", "niro_self.sqlite3")',
    'DB_PATH = os.getenv("DB_PATH", "niro_self.sqlite3")\nGAME_IMAGE_PATH = os.getenv("GAME_IMAGE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_start.png"))',
    "تنظیم مسیر عکس"
)

# ارسال پیام اولیه همراه عکس
replace_once(
'''                "🤝 بازیکن دوم برای ورود، دکمه پیوستن را بزند.\\n"
                "🔒 پس از پیوستن، مبلغ بازی قفل و نتیجه با تاس تلگرام مشخص می‌شود.")
        sent = await m.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=group_game_keyboard(gid))
        with db() as c: c.execute("UPDATE games SET message_id=? WHERE id=?", (sent.message_id, gid))''',
'''                "🤝 بازیکن دوم برای ورود، دکمه پیوستن را بزند.\\n"
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
        with db() as c: c.execute("UPDATE games SET message_id=? WHERE id=?", (sent.message_id, gid))''',
    "ارسال عکس هنگام ایجاد بازی"
)

# تابع ویرایش هوشمند متن یا کپشن
replace_once(
'''async def game_callbacks(update, context):''',
'''async def edit_game_message(q, text, **kwargs):
    if q.message and q.message.photo:
        return await q.edit_message_caption(caption=text, **kwargs)
    return await q.edit_message_text(text=text, **kwargs)


async def game_callbacks(update, context):''',
    "افزودن تابع ویرایش پیام عکس‌دار"
)

# ویرایش پیام لغو
replace_once(
'''        return await q.edit_message_text("❌ این چالش توسط سازنده لغو شد.")''',
'''        return await edit_game_message(q, "❌ این چالش توسط سازنده لغو شد.")''',
    "لغو بازی"
)

# ویرایش پیام شروع شرط‌بندی
replace_once(
'''    await q.edit_message_text(
        "🔐 <b>شرط‌بندی مخفی NIRO شروع شد!</b>\\n\\n"
        "💎 مبلغ شرط هر بازیکن قفل شد.\\n"
        "🎯 نتیجه بدون نمایش تاس و به‌صورت تصادفی تعیین می‌شود...",
        parse_mode=ParseMode.HTML
    )''',
'''    await edit_game_message(
        q,
        "🔐 <b>شرط‌بندی مخفی NIRO شروع شد!</b>\\n\\n"
        "💎 مبلغ شرط هر بازیکن قفل شد.\\n"
        "🎯 نتیجه بدون نمایش تاس و به‌صورت تصادفی تعیین می‌شود...",
        parse_mode=ParseMode.HTML
    )''',
    "نمایش شروع شرط‌بندی روی عکس"
)

# ویرایش پیام نتیجه نهایی
replace_once(
'''        await q.edit_message_text(
            "🎮 <b>نتیجه نهایی شرط‌بندی NIRO</b>\\n\\n"''',
'''        await edit_game_message(
            q,
            "🎮 <b>نتیجه نهایی شرط‌بندی NIRO</b>\\n\\n"''',
    "نمایش نتیجه نهایی روی عکس"
)

p.write_text(s, encoding="utf-8")
print("\\nهمه تغییرات با موفقیت ذخیره شدند.")
