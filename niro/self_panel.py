import os
import json
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from telethon import TelegramClient, events, Button
from telethon.tl.functions.users import GetFullUserRequest

# ---------- CONFIG ----------
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION = os.getenv("NIRO_SESSION", "niro_user")
TZ = os.getenv("NIRO_TZ", "Asia/Kabul")
SETTINGS_FILE = "self_panel_settings.json"

if not API_ID or not API_HASH:
    raise SystemExit("Set API_ID and API_HASH environment variables first.")

client = TelegramClient(SESSION, API_ID, API_HASH)

DEFAULTS = {
    "bio_base": "",
    "surname_base": "",
    "bio_clock": False,
    "surname_clock": False,
    "clock_style": 0,
    "auto_reply": False,
    "reply_text": "سلام، پیام شما دریافت شد. بعداً پاسخ می‌دهم.",
    "reply_friends_only": False,
    "reply_start": "00:00",
    "reply_end": "23:59",
    "friends": [],
    "enemies": [],
    "media_save": False,
    "typing": False,
    "profile_initialized": False,
}
settings = DEFAULTS.copy()
input_mode = None
last_replied = {}
last_clock_bio = None
last_clock_surname = None

CLOCK_STYLES = [
    lambda s: s,
    lambda s: "[" + s + "]",
    lambda s: "⌚ " + s,
    lambda s: "• " + s,
    lambda s: s.replace("0", "０").replace("1", "１").replace("2", "２").replace("3", "３").replace("4", "４").replace("5", "５").replace("6", "６").replace("7", "７").replace("8", "８").replace("9", "９"),
    lambda s: s.translate(str.maketrans("0123456789", "⓪①②③④⑤⑥⑦⑧⑨")),
]

def load_settings():
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for key in DEFAULTS:
                if key in saved:
                    settings[key] = saved[key]
        except Exception as exc:
            print("Settings load error:", exc)

def save_settings():
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def now():
    return datetime.now(ZoneInfo(TZ))

def clock_value():
    raw = now().strftime("%H:%M")
    return CLOCK_STYLES[int(settings.get("clock_style", 0)) % len(CLOCK_STYLES)](raw)

def in_time_window():
    current = now().strftime("%H:%M")
    start = settings.get("reply_start", "00:00")
    end = settings.get("reply_end", "23:59")
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end

def status_text():
    return (
        "⚡ <b>NIRO SELF | پنل اکانت</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"🕒 ساعت بیو: {'🟢 روشن' if settings['bio_clock'] else '🔴 خاموش'}\n"
        f"🕒 ساعت نام: {'🟢 روشن' if settings['surname_clock'] else '🔴 خاموش'}\n"
        f"💬 پاسخ خودکار: {'🟢 روشن' if settings['auto_reply'] else '🔴 خاموش'}\n"
        f"👥 فقط دوستان: {'🟢' if settings['reply_friends_only'] else '🔴'}\n"
        f"💾 ذخیره رسانه: {'🟢 روشن' if settings['media_save'] else '🔴 خاموش'}\n"
        f"⌨️ حالت تایپ: {'🟢 روشن' if settings['typing'] else '🔴 خاموش'}\n"
        f"🕰 ساعت فعلی: {clock_value()}\n"
        f"👥 دوستان: {len(settings['friends'])} | 🚫 مسدود از پاسخ: {len(settings['enemies'])}\n"
        "━━━━━━━━━━━━━━\n"
        "از دکمه‌ها برای مدیریت استفاده کن."
    )

def main_buttons():
    return [
        [Button.inline("🕒 ساعت بیو", b"toggle_bio_clock"),
         Button.inline("🕒 ساعت نام", b"toggle_surname_clock")],
        [Button.inline("🎨 فونت ساعت", b"clock_style"),
         Button.inline("✍️ تنظیم بیو", b"set_bio")],
        [Button.inline("👤 تنظیم نام خانوادگی", b"set_surname"),
         Button.inline("💬 پاسخ خودکار", b"toggle_reply")],
        [Button.inline("📝 متن پاسخ", b"set_reply"),
         Button.inline("⏰ زمان پاسخ", b"set_schedule")],
        [Button.inline("👥 فقط دوستان", b"toggle_friends_only"),
         Button.inline("👥 مدیریت دوستان", b"friends")],
        [Button.inline("⌨️ حالت تایپ", b"toggle_typing"),
         Button.inline("👥 لیست دشمنان", b"enemies")],
        [Button.inline("🚫 لیست دشمنان", b"enemies"),
         Button.inline("💾 ذخیره رسانه", b"toggle_media")],
        [Button.inline("📊 وضعیت", b"status"),
         Button.inline("🔄 تازه‌سازی", b"refresh")],
    ]

def back_buttons():
    return [[Button.inline("🔙 بازگشت به پنل", b"refresh")]]

async def edit_panel(event, text=None, buttons=None):
    try:
        await event.edit(text or status_text(), buttons=buttons or main_buttons(), parse_mode="html")
    except Exception:
        pass

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.پنل$|^\.panel$"))
async def panel_open(event):
    me = await client.get_me()
    if not event.is_private or event.chat_id != me.id:
        return
    await event.respond(status_text(), buttons=main_buttons(), parse_mode="html")

@client.on(events.CallbackQuery)
async def panel_buttons_handler(event):
    global input_mode
    data = event.data.decode(errors="ignore")
    if not data.startswith(("toggle_", "clock_", "set_", "schedule", "friends", "enemies", "status", "refresh", "friend_", "enemy_")):
        return

    if data == "refresh":
        await edit_panel(event)
    elif data == "toggle_bio_clock":
        settings["bio_clock"] = not settings["bio_clock"]
        save_settings()
        await event.answer("ساعت بیو " + ("روشن شد" if settings["bio_clock"] else "خاموش شد"))
        await edit_panel(event)
    elif data == "toggle_surname_clock":
        settings["surname_clock"] = not settings["surname_clock"]
        save_settings()
        await event.answer("ساعت نام " + ("روشن شد" if settings["surname_clock"] else "خاموش شد"))
        await edit_panel(event)
    elif data == "clock_style":
        settings["clock_style"] = (int(settings.get("clock_style", 0)) + 1) % len(CLOCK_STYLES)
        save_settings()
        await event.answer(f"فونت ساعت: {clock_value()}")
        await edit_panel(event)
    elif data == "set_bio":
        input_mode = "bio"
        await event.answer()
        await event.respond("📝 بیوی جدید را در Saved Messages بفرست. برای پاک‌کردن بیو، پیام خالی/علامت - بفرست.")
    elif data == "set_surname":
        input_mode = "surname"
        await event.answer()
        await event.respond("👤 نام خانوادگی جدید را ارسال کن. برای پاک‌کردن، - بفرست.")
    elif data == "toggle_reply":
        settings["auto_reply"] = not settings["auto_reply"]
        save_settings()
        await event.answer("پاسخ خودکار " + ("فعال شد" if settings["auto_reply"] else "خاموش شد"))
        await edit_panel(event)
    elif data == "set_reply":
        input_mode = "reply"
        await event.answer()
        await event.respond("💬 متن پاسخ خودکار را بفرست:")
    elif data == "set_schedule":
        input_mode = "schedule"
        await event.answer()
        await event.respond("⏰ زمان شروع و پایان را به شکل زیر ارسال کن:\n08:00-22:30\nبرای تمام روز: 00:00-23:59")
    elif data == "toggle_friends_only":
        settings["reply_friends_only"] = not settings["reply_friends_only"]
        save_settings()
        await event.answer("فقط دوستان " + ("فعال شد" if settings["reply_friends_only"] else "خاموش شد"))
        await edit_panel(event)
    elif data == "friends":
        input_mode = "friends"
        await event.answer()
        await event.respond(
            "👥 مدیریت دوستان\nبرای افزودن شناسه یا username ارسال کن.\n"
            "برای حذف، اول علامت - بگذار؛ مثال:\n@username\n-@username\n"
            "برای نمایش لیست بنویس: list"
        )
    elif data == "enemies":
        input_mode = "enemies"
        await event.answer()
        await event.respond(
            "🚫 لیست نادیده‌گرفتن پاسخ خودکار\nشناسه یا username را ارسال کن.\n"
            "برای حذف، اول - بگذار. برای نمایش: list"
        )
    elif data == "toggle_typing":
        settings["typing"] = not settings["typing"]
        save_settings()
        await event.answer("حالت تایپ " + ("روشن شد" if settings["typing"] else "خاموش شد"))
        await edit_panel(event)
    elif data == "toggle_media":
        settings["media_save"] = not settings["media_save"]
        save_settings()
        await event.answer("ذخیره رسانه " + ("فعال شد" if settings["media_save"] else "خاموش شد"))
        await edit_panel(event)
    elif data == "status":
        await event.answer()
        await edit_panel(event, status_text(), main_buttons())
    elif data.startswith("friend_") or data.startswith("enemy_"):
        await event.answer()

@client.on(events.NewMessage(outgoing=True))
async def saved_messages_input(event):
    global input_mode
    me = await client.get_me()
    if not event.is_private or event.chat_id != me.id:
        return
    text = (event.raw_text or "").strip()
    if text in (".پنل", ".panel") or not input_mode:
        return

    mode = input_mode
    input_mode = None

    if mode == "bio":
        settings["bio_base"] = "" if text == "-" else text
        save_settings()
        await update_profile()
        await event.respond("✅ بیو ذخیره و اعمال شد.")

    elif mode == "surname":
        settings["surname_base"] = "" if text == "-" else text
        save_settings()
        await update_profile()
        await event.respond("✅ نام خانوادگی ذخیره و اعمال شد.")

    elif mode == "reply":
        settings["reply_text"] = text
        save_settings()
        await event.respond("✅ متن پاسخ خودکار ذخیره شد.")

    elif mode == "schedule":
        try:
            start, end = text.split("-", 1)
            datetime.strptime(start.strip(), "%H:%M")
            datetime.strptime(end.strip(), "%H:%M")
            settings["reply_start"] = start.strip()
            settings["reply_end"] = end.strip()
            save_settings()
            await event.respond("✅ زمان‌بندی ذخیره شد.")
        except Exception:
            await event.respond("❌ قالب اشتباه است. نمونه: 08:00-22:30")

    elif mode in ("friends", "enemies"):
        key = "friends" if mode == "friends" else "enemies"
        if text.lower() == "list":
            values = settings[key]
            await event.respond("📋 لیست:\n" + ("\n".join(map(str, values)) if values else "خالی است"))
            return
        remove = text.startswith("-")
        value = text[1:].strip() if remove else text
        if value:
            values = settings[key]
            if remove:
                settings[key] = [v for v in values if str(v).lower() != value.lower()]
                await event.respond("🗑 حذف شد (اگر در لیست بود).")
            else:
                if value not in values:
                    values.append(value)
                await event.respond("✅ به لیست اضافه شد.")
            save_settings()

async def update_profile():
    bio = settings.get("bio_base", "")
    surname = settings.get("surname_base", "")
    clock = clock_value()
    if settings["bio_clock"]:
        bio = (bio + " " + clock).strip()
    if settings["surname_clock"]:
        surname = (surname + " " + clock).strip()
    try:
        await client.edit_profile(about=bio[:70], last_name=surname[:64])
    except Exception as exc:
        print("Profile update failed:", exc)

async def clock_task():
    global last_clock_bio, last_clock_surname
    while True:
        try:
            if settings["bio_clock"] or settings["surname_clock"]:
                value = clock_value()
                if value != last_clock_bio or value != last_clock_surname:
                    await update_profile()
                    last_clock_bio = value
                    last_clock_surname = value
        except Exception as exc:
            print("Clock task error:", exc)
        await asyncio.sleep(60)

def matches_list(sender, values):
    sender_id = str(sender.id)
    username = ("@" + sender.username.lower()) if sender.username else ""
    return any(str(v).lower() in (sender_id, username, (sender.username or "").lower()) for v in values)

@client.on(events.NewMessage(incoming=True))
async def auto_reply_handler(event):
    if not settings["auto_reply"] or not event.is_private:
        return
    sender = await event.get_sender()
    if not sender or getattr(sender, "bot", False):
        return
    me = await client.get_me()
    if sender.id == me.id:
        return
    if matches_list(sender, settings["enemies"]):
        return
    if settings["reply_friends_only"] and not matches_list(sender, settings["friends"]):
        return
    if not in_time_window():
        return
    now_ts = datetime.now().timestamp()
    if now_ts - last_replied.get(sender.id, 0) < 60:
        return
    last_replied[sender.id] = now_ts
    try:
        if settings["typing"]:
            async with client.action(event.chat_id, "typing"):
                await asyncio.sleep(1.5)
                await event.reply(settings["reply_text"])
        else:
            await event.reply(settings["reply_text"])
    except Exception as exc:
        print("Auto reply error:", exc)

@client.on(events.NewMessage(incoming=True))
async def media_saver(event):
    if not settings["media_save"] or not event.is_private:
        return
    if not event.message.media:
        return
    sender = await event.get_sender()
    if not sender:
        return
    if matches_list(sender, settings["enemies"]):
        return
    try:
        path = await event.download_media()
        if path:
            await client.send_file("me", path, caption="💾 ذخیره رسانه خودکار")
            try:
                os.remove(path)
            except OSError:
                pass
    except Exception as exc:
        print("Media save error:", exc)

async def main():
    load_settings()
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit(
            "NIRO session is not authorized. "
            "Authorize this account securely before deployment."
        )
    me = await client.get_me()
    if not settings.get("profile_initialized"):
        try:
            full = await client(GetFullUserRequest(me))
            settings["bio_base"] = getattr(full.full_user, "about", "") or ""
            settings["surname_base"] = me.last_name or ""
            settings["profile_initialized"] = True
            save_settings()
        except Exception as exc:
            print("Could not read initial profile (will not overwrite it):", exc)
    print(f"NIRO SELF connected: {me.id}")
    asyncio.create_task(clock_task())
    print("Saved Messages: send .پنل")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

