from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, InlineQueryHandler, MessageHandler, filters
import logging
import time
import json
import os
import asyncio

TOKEN = os.getenv("HELPER_TOKEN", "")  # Set via environment; no embedded token
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMMAND_FILE = os.path.join(BASE_DIR, "selfbot_commands.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
REACTION_RESULT_FILE = os.path.join(BASE_DIR, "reaction_result.json")

if not os.path.exists(COMMAND_FILE):
    with open(COMMAND_FILE, 'w', encoding='utf-8') as f:
        json.dump({'pending': False, 'command': '', 'user_id': 0, 'timestamp': 0}, f, ensure_ascii=False, indent=4)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

HELP_TEXTS = {
    "time": """
⏰ <b>مدیریت ساعت</b>

<b>دستورات قابل کپی:</b>
<code>تایم روشن</code>
<code>تایم خاموش</code>

<b>کاربرد:</b>
نمایش زمان کنار نام کاربری
آپدیت خودکار هر دقیقه
فونت‌های مختلف برای زمان

<b>فونت‌های موجود:</b>
𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗 - فونت 1
𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵 - فونت 2  
０１２３４５６７８９ - فونت 3
𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫 - فونت 4
𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡 - فونت 5
0҉1҉2҉3҉4҉5҉6҉7҉8҉9҉ - فونت 6
""",
    "oneclick": """
⚡ <b>یک کلیک</b>

<b>مدیریت سریع با یک کلیک:</b>
• تنظیمات ساعت
• فرمت‌های متن

<b>کاربرد:</b>
با یک کلیک به تمام تنظیمات سریع دسترسی داشته باشید.
""",
    "instagram": """
📥 <b>دانلودر اینستاگرام</b>

<b>دستور قابل کپی:</b>
<code>اینستا لینک_پست</code>

<b>مثال‌ها:</b>
<code>اینستا https://www.instagram.com/reel/DOkym3fCFqg/</code>
<code>اینستا https://www.instagram.com/p/CzuF4KQqJ7q/</code>
<code>اینستا https://www.instagram.com/tv/Cxxxxxxxx/</code>

<b>کاربرد:</b>
• دانلود پست‌های اینستاگرام
• دانلود ریل‌ ها و ویدیو ها
• دانلود عکس‌های پست

<b>قابلیت‌ها:</b>
✅ دانلود با کیفیت اصلی
✅ نمایش توضیحات پست
✅ نمایش اطلاعات کاربر
✅ آپلود در همان چت
""",
    "id": """
🆔 <b>سیستم آیدی پیشرفته</b>

<b>دستور قابل کپی:</b>
<code>ایدی</code>

<b>دو حالت استفاده:</b>

1️⃣ <b>بدون ریپلای:</b>
<code>ایدی</code>
• نمایش اطلاعات خودتان
• نمایش اطلاعات چت فعلی
• نمایش آیدی عددی

2️⃣ <b>با ریپلای:</b>
<code>ایدی</code> (روی پیام کاربر ریپلای)
• نمایش اطلاعات کامل کاربر
• نمایش گروه‌های مشترک  
• نمایش آیدی و یوزرنیم

<b>اطلاعات نمایش داده شده:</b>
✅ آیدی عددی کاربر
✅ یوزرنیم و نام کامل
✅ وضعیت پریمیوم
✅ تعداد عکس‌های پروفایل
✅ آیدی چت و عنوان
✅ تعداد اعضا (در گروه)
✅ گروه‌های مشترک (در صورت وجود)

<b>مثال خروجی:</b>
• اطلاعات شما + چت فعلی
• یا اطلاعات کاربر ریپلای شده
""",
    "photo": """
📸 <b>ذخیره عکس تایمدار</b>

<b>دستور قابل کپی:</b>
<code>عکس سیو</code> (ریپلای روی عکس)

<b>کاربرد:</b>
ذخیره دستی عکس‌های تایمدار
ارسال اطلاعات کامل کاربر

<b>نکته:</b>
فقط روی عکس‌های تایمدار کار می‌کند
عکس معمولی قابل ذخیره نیست
""",
    "backup": """
💾 <b>پشتیبان‌گیری</b>

<b>دستور قابل کپی:</b>
<code>سیو @یوزرنیم</code>

<b>مثال:</b>
<code>سیو @username</code>

<b>کاربرد:</b>
ذخیره تاریخچه چت در فایل متنی
ارسال فایل به پیام‌های ذخیره شده
""",
    "font": """
🔤 <b>مدیریت فونت</b>

<b>دستورات قابل کپی:</b>
<code>لیست فونت</code>
<code>تنظیم فونت 1</code> تا <code>تنظیم فونت 6</code>

<b>کاربرد:</b>
تغییر فونت نمایش زمان
پیش‌نمایش فونت‌های مختلف
اعمال فونت روی زمان به صورت زنده
""",
    "price": """
💱 <b>قیمت ارز</b>

<b>دستور قابل کپی:</b>
<code>قیمت ارز</code>

<b>مثال‌ها:</b>
<code>قیمت BTC</code>
<code>قیمت ETH</code>
<code>قیمت TON</code>

<b>کاربرد:</b>
نمایش قیمت لحظه‌ای ارزهای دیجیتال
نمایش قیمت تومانی و دلاری
نمایش تغییرات 24 ساعته
میتوانید اسم ارزو رو به فارسی بزارید
""",
    "spam": """
🔁 <b>ارسال اسپم</b>

<b>دستور قابل کپی:</b>
<code>اسپم تعداد متن</code>

<b>مثال‌ها:</b>
<code>اسپم 10 سلام</code>
<code>اسپم 5 تست</code>

<b>کاربرد:</b>
ارسال پیام تکراری
حداکثر 50 پیام در یک دستور
قابلیت ریپلای روی پیام
""",
    "format": """
🎨 <b>سیستم فرمت خودکار HTML</b>

<b>دستورات قابل کپی:</b>
<code>فرمت بولد روشن</code>
<code>فرمت بولد خاموش</code>
<code>فرمت ایتالیک روشن</code>
<code>فرمت ایتالیک خاموش</code>
<code>فرمت زیرخط روشن</code>
<code>فرمت زیرخط خاموش</code>
<code>فرمت خط‌خورده روشن</code>
<code>فرمت خط‌خورده خاموش</code>
<code>فرمت اسپویلر روشن</code>
<code>فرمت اسپویلر خاموش</code>
<code>فرمت کد روشن</code>
<code>فرمت کد خاموش</code>
<code>فرمت پیش‌فرمت روشن</code>
<code>فرمت پیش‌فرمت خاموش</code>
<code>فرمت نقل‌قول روشن</code>
<code>فرمت نقل‌قول خاموش</code>
<code>فرمت وضعیت</code>
<code>فرمت ریست</code>

<b>کاربرد:</b>
تبدیل خودکار پیام‌ ها به فرمت‌ های مختلف
پشتیبانی از تمام تگ‌های HTML تلگرام
امکان استفاده همزمان از چندین فرمت

<b>فرمت‌های پشتیبانی شده:</b>
• <b>بولد</b> - <b>متن بولد</b>
• <i>ایتالیک</i> - <i>متن ایتالیک</i>
• <u>زیرخط</u> - <u>متن زیرخط دار</u>
• <s>خط‌خورده</s> - <s>متن خط خورده</s>
• <code>کد</code> - <code>متن کد</code>
• <pre>پیش‌فرمت</pre> - <pre>متن پیش‌فرمت</pre>
• <blockquote>نقل‌قول</blockquote> - <blockquote>متن نقل قول</blockquote>
""",
    "enemy": """
👿 <b>مدیریت دشمنان</b>

<b>دستورات قابل کپی:</b>
<code>دشمن</code> (ریپلای روی پیام کاربر)
<code>حذف دشمن</code> (ریپلای روی پیام کاربر)
<code>لیست دشمن</code>
<code>دشمنان</code>
<code>پاک کردن دشمنان</code>

<b>کاربرد:</b>
افزودن کاربر به لیست دشمنان
ارسال خودکار فحش رندوم به دشمنان
مدیریت لیست دشمنان
نمایش اطلاعات کامل دشمنان
حذف دشمن از لیست
""",
    "autoreply": """
🤖 <b>پاسخ خودکار</b>

<b>دستورات قابل کپی:</b>
<code>پاسخ افزودن سلام|سلام چطوری</code>
<code>پاسخ حذف سلام</code>
<code>پاسخ لیست</code>

<b>مثال‌ها:</b>
<code>پاسخ افزودن سلا|سلام عزیزم</code>
<code>پاسخ افزودن چطوری|خوبم ممنون</code>
<code>پاسخ حذف سلا</code>

<b>کاربرد:</b>
تنظیم پاسخ خودکار برای کلمات خاص
لیست پاسخ‌ های تنظیم شده
""",
    "insult": """
💢 <b>مدیریت فحش‌ها</b>

<b>دستورات قابل کپی:</b>
<code>فحش افزودن متن فحش</code>
<code>فحش حذف متن فحش</code>

<b>مثال‌ها:</b>
<code>فحش افزودن تو احمقی</code>
<code>فحش افزودن برو گمشو</code>
<code>فحش حذف تو احمقی</code>

<b>کاربرد:</b>
افزودن فحش‌های جدید به لیست
حذف فحش ‌های موجود
ارسال رندوم فحش به دشمنان
""",
    "online": """
🌐 <b>حالت همیشه آنلاین</b>

<b>دستورات قابل کپی:</b>
<code>آنلاین روشن</code>
<code>آنلاین خاموش</code>

<b>کاربرد:</b>
فعال کردن حالت همیشه آنلاین
نمایش آنلاین دائمی در تلگرام
مناسب برای نشان دادن فعالیت دائمی
""",
    "lock": """
🔒 <b>سیستم قفل پیوی</b>

<b>دستورات قابل کپی:</b>
<code>همه روشن</code>
<code>همه خاموش</code>
<code>مدیا روشن</code>
<code>مدیا خاموش</code>
<code>استیکر روشن</code>
<code>استیکر خاموش</code>
<code>فوروارد روشن</code>
<code>فوروارد خاموش</code>
<code>وویس روشن</code>
<code>وویس خاموش</code>
<code>پیام روشن</code>
<code>پیام خاموش</code>
<code>فایل روشن</code>
<code>فایل خاموش</code>
<code>وضعیت قفل</code>
<code>ریست قفل</code>
<code>راهنمای قفل</code>

<b>کاربرد:</b>
محدود کردن ارسال انواع پیام در پیوی
حذف خودکار پیام‌های غیرمجاز
مدیریت دسترسی ‌های کاربران
نمایش وضعیت قفل ‌ها
""",
    "antilogin": """
🛡️ <b>سیستم انتی لاگین</b>

<b>دستورات قابل کپی:</b>
<code>انتی لاگین روشن</code>
<code>انتی لاگین خاموش</code>
<code>انتی لاگین</code>

<b>کاربرد:</b>
منقضی کردن کد اتوماتیک
جلوگیری از ورود به اکانت
""",
    "reaction": """
🎭 <b>سیستم ریکشن خودکار</b>

<b>دستورات قابل کپی:</b>
<code>ریکت ایموجی</code> (ریپلای روی کاربر)
<code>حذف ریکت</code> (ریپلای روی کاربر)
<code>لیست ریکت</code>
<code>پاکسازی ریکت</code>

<b>مثال‌ها:</b>
<code>ریکت 🚀</code> (ریپلای)
<code>ریکت ❤️</code> (ریپلای)
<code>حذف ریکت</code> (ریپلای)

<b>کاربرد:</b>
تنظیم ریکشن خودکار برای کاربران خاص
اعمال ریکشن روی تمام پیام‌ های کاربر
مدیریت لیست ریکشن‌ ‌ها
حذف ریکشن کاربران
""",
    "edit": """
✏️ <b>ویرایش سریع پیام</b>

<b>دستور قابل کپی:</b>
<code>ویرایش کلمه_قدیمی به کلمه_جدید</code> (ریپلای)

<b>مثال‌ها:</b>
<code>ویرایش سلان به سلام</code>
<code>ویرایش احمق به عزیز</code>
<code>ویرایش بد به خوب</code>

<b>کاربرد:</b>
جایگزینی سریع کلمه در پیام
ریپلای روی پیام مورد نظر
حذف خودکار پیام دستور
جایگزینی فقط کلمه مشخص شده
""",
    "banner": """
📢 <b>سیستم مدیریت بنر</b>

<b>دستورات قابل کپی:</b>
<code>تنظیم بنر</code> (ریپلای روی پیام)
<code>بنر همگانی کد</code>
<code>لیست بنرها</code>
<code>بنر همگانی خاموش</code>
<code>بنر ارسال کد</code>
<code>زمان بنر دقیقه</code>

<b>مثال‌ها:</b>
<code>تنظیم بنر</code> (ریپلای)
<code>بنر همگانی 1</code>
<code>بنر ارسال 1</code>
<code>زمان بنر 5</code>

<b>کاربرد:</b>
ثبت پیام به عنوان بنر
ارسال همگانی به گروه‌ها و سوپرگروه ‌ها
مدیریت بنرهای ثبت شده
تنظیم زمان بین ارسال‌ ها
ارسال فوری بنر
""",
    "download": """
📥 <b>دانلودر تلگرام</b>

<b>دستور قابل کپی:</b>
<code>دانلود لینک_پست</code>

<b>مثال‌ها:</b>
<code>دانلود https://t.me/channel/123</code>
<code>دانلود https://t.me/username/456</code>
<code>دانلود https://t.me/c/channel_id/post_id</code>

💡 <b>کاربرد اصلی:</b>
دانلود پست کانال های اسکم یا گروه ها
""",
    "new": """
🆕 <b>دستورات مربوط به کانال و گروه</b>

<b>دستورات قابل کپی:</b>
<code>پینگ</code>
<code>تعداد کانال ها</code>
<code>تعداد گروه ها</code>
<code>خروج همه کانال</code>
<code>خروج همه گروه</code>

<b>کاربرد:</b>
• <code>پینگ</code> - بررسی سرعت ربات
• <code>تعداد کانال ها</code> - نمایش آمار دقیق کانال‌ها
• <code>تعداد گروه ها</code> - نمایش آمار دقیق گروه‌ها
• <code>خروج همه کانال</code> - خروج از تمام کانال‌ها با تاخیر
• <code>خروج همه گروه</code> - خروج از تمام گروه‌ها با تاخیر

<b>نکته:</b>
تاخیر 4 ثانیه‌ ای برای جلوگیری از محدودیت
""",
}

def send_command_to_self_bot(command, user_id):
    try:
        if not os.path.exists(COMMAND_FILE) or os.path.getsize(COMMAND_FILE) == 0:
            data = {'pending': False, 'command': '', 'user_id': 0, 'timestamp': 0}
        else:
            with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        data['pending'] = True
        data['command'] = command
        data['user_id'] = user_id
        data['timestamp'] = time.time()
        
        with open(COMMAND_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False

def get_font_preview(font_num):
    sample = "12:34"
    fonts = {
        1: "".join(["𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"[int(d)] if d.isdigit() else d for d in sample]),
        2: "".join(["𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"[int(d)] if d.isdigit() else d for d in sample]),
        3: "".join(["０１２３４５６７８９"[int(d)] if d.isdigit() else d for d in sample]),
        4: "".join(["𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"[int(d)] if d.isdigit() else d for d in sample]),
        5: "".join(["𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"[int(d)] if d.isdigit() else d for d in sample]),
        6: "".join(["0҉1҉2҉3҉4҉5҉6҉7҉8҉9҉"[int(d)*2:(int(d)*2)+2] if d.isdigit() else d for d in sample])
    }
    return fonts.get(font_num, sample)

def get_font_buttons(user_id, from_page=1):
    keyboard = [
        [
            InlineKeyboardButton("𝟏𝟐:𝟑𝟒", callback_data=f"font_1_{user_id}_{from_page}"),
            InlineKeyboardButton("𝟭𝟮:𝟯𝟰", callback_data=f"font_2_{user_id}_{from_page}"),
            InlineKeyboardButton("１２:３４", callback_data=f"font_3_{user_id}_{from_page}")
        ],
        [
            InlineKeyboardButton("𝟣𝟤:𝟥𝟦", callback_data=f"font_4_{user_id}_{from_page}"),
            InlineKeyboardButton("𝟙𝟚:𝟛𝟜", callback_data=f"font_5_{user_id}_{from_page}"),
            InlineKeyboardButton("1҉2҉:3҉4҉", callback_data=f"font_6_{user_id}_{from_page}")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به ساعت", callback_data=f"clock_back_{user_id}_{from_page}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_clock_buttons(user_id, from_page=1):
    settings = load_settings()
    time_status = settings.get('time_status', 'خاموش')
    font_status = settings.get('font', 1)
    
    time_emoji = "🟢" if time_status == "روشن" else "🔴"
    time_text = f"{time_emoji} {time_status}" if time_status == "روشن" else f"{time_emoji} خاموش"
    font_preview = get_font_preview(int(font_status))
    
    keyboard = [
        [
            InlineKeyboardButton(f"⏰ وضعیت ساعت: {time_text}", callback_data=f"time_status_{user_id}_{from_page}")
        ],
        [
            InlineKeyboardButton("✅ روشن کردن ساعت", callback_data=f"time_on_{user_id}_{from_page}"),
            InlineKeyboardButton("❌ خاموش کردن ساعت", callback_data=f"time_off_{user_id}_{from_page}")
        ],
        [
            InlineKeyboardButton(f"🔤 فونت فعلی: {font_preview}", callback_data=f"help_fonts_{user_id}_{from_page}")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به یک کلیک", callback_data=f"oneclick_back_{user_id}_{from_page}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_oneclick_buttons(user_id, from_page=1):
    keyboard = [
        [
            InlineKeyboardButton("⏰ مدیریت ساعت", callback_data=f"oneclick_time_{user_id}_{from_page}"),
            InlineKeyboardButton("🎨 فرمت متن", callback_data=f"oneclick_format_{user_id}_{from_page}")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"help_back_{user_id}_{from_page}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_format_buttons(user_id, from_page=1):
    settings = load_settings()
    format_settings = settings.get('formats', {})
    
    keyboard = []
    
    formats = [
        ("بولد", "bold"),
        ("ایتالیک", "italic"),
        ("زیرخط", "underline"),
        ("خط خورده", "strike"),
        ("اسپویلر", "spoiler"),
        ("کد", "code"),
        ("پیش‌فرمت", "pre"),
        ("نقل‌قول", "quote")
    ]
    
    row = []
    for i, (name, key) in enumerate(formats):
        status = format_settings.get(key, False)
        emoji = "✅" if status else "⬜"
        row.append(InlineKeyboardButton(
            f"{emoji} {name}", 
            callback_data=f"format_{key}_{user_id}_{from_page}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🔄 ریست همه فرمت‌ها", callback_data=f"format_reset_{user_id}_{from_page}"),
        InlineKeyboardButton("📊 وضعیت فرمت‌ها", callback_data=f"format_status_{user_id}_{from_page}")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به یک کلیک", callback_data=f"oneclick_back_{user_id}_{from_page}")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_page1(user_id):
    keyboard = [
        [
            InlineKeyboardButton("● ایدی ●", callback_data=f"help_id_{user_id}_1"),
            InlineKeyboardButton("● یک کلیک ⚡", callback_data=f"help_oneclick_{user_id}_1")
        ],
        [
            InlineKeyboardButton("● عکس تایمدار ●", callback_data=f"help_photo_{user_id}_1"),
        ],
        [
            InlineKeyboardButton("● پشتیبان‌گیری ●", callback_data=f"help_backup_{user_id}_1"),
            InlineKeyboardButton("● مدیریت فونت ●", callback_data=f"help_font_{user_id}_1")
        ],
        [
            InlineKeyboardButton("● قیمت ارز ●", callback_data=f"help_price_{user_id}_1"),
        ],
        [
            InlineKeyboardButton("● فرمت متن ●", callback_data=f"help_format_{user_id}_1"),
            InlineKeyboardButton("● اسپم ●", callback_data=f"help_spam_{user_id}_1")
        ],
        [
            InlineKeyboardButton("● مدیریت دشمنان ●", callback_data=f"help_enemy_{user_id}_1"),
        ],
        [
            InlineKeyboardButton("● پاسخ خودکار ●", callback_data=f"help_autoreply_{user_id}_1"),
        ],
        [
            InlineKeyboardButton("● صفحه 2 → ●", callback_data=f"page2_{user_id}"),
            InlineKeyboardButton("● بست ●", callback_data=f"close_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_page2(user_id):
    keyboard = [
        [
            InlineKeyboardButton("● سیستم فحش ●", callback_data=f"help_insult_{user_id}_2"),
            InlineKeyboardButton("● همیشه آنلاین ●", callback_data=f"help_online_{user_id}_2")
        ],
        [
            InlineKeyboardButton("● قفل پیوی ●", callback_data=f"help_lock_{user_id}_2"),
        ],
        [
            InlineKeyboardButton("●️ انتی لاگین ●", callback_data=f"help_antilogin_{user_id}_2"),
            InlineKeyboardButton("● ریکشن خودکار ●", callback_data=f"help_reaction_{user_id}_2")
        ],
        [
            InlineKeyboardButton("● ویرایش سریع ●", callback_data=f"help_edit_{user_id}_2"),
        ],
        [
            InlineKeyboardButton("● سیستم بنر ●", callback_data=f"help_banner_{user_id}_2"),
            InlineKeyboardButton("● اینستاگرام ●", callback_data=f"help_instagram_{user_id}_2")
        ],
        [
            InlineKeyboardButton("● دانلود تلگرام ●", callback_data=f"help_download_{user_id}_2"),
        ],
        [
            InlineKeyboardButton("● مدیریت گروه/کانال ●", callback_data=f"help_new_{user_id}_2"),
        ],
        [
            InlineKeyboardButton("← صفحه 1", callback_data=f"page1_{user_id}"),
            InlineKeyboardButton("❌ بستن", callback_data=f"close_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button(user_id, from_page=1):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"help_back_{user_id}_{from_page}")]
    ])

def get_reopen_button(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 بازکردن پنل", callback_data=f"reopen_{user_id}")]
    ])

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = "<b>🎛 پنل مدیریت سلف</b>\n\n💡 <i>صفحه اول - 10 قابلیت اصلی</i>"
    await update.message.reply_text(text, reply_markup=get_main_menu_page1(user_id), parse_mode='HTML')

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip().lower()
    
    if query == "panel":
        user_id = update.inline_query.from_user.id
        
        results = [
            InlineQueryResultArticle(
                id="1",
                title="🎛 پنل مدیریت سلف - صفحه 1",
                description="10 قابلیت اصلی - مدیریت کامل",
                input_message_content=InputTextMessageContent(
                    message_text="<b>🎛 پنل مدیریت سلف</b>\n\n💡 <i>صفحه اول - 10 قابلیت اصلی</i>",
                    parse_mode='HTML'
                ),
                reply_markup=get_main_menu_page1(user_id)
            ),
            InlineQueryResultArticle(
                id="2",
                title="🎛 پنل مدیریت سلف - صفحه 2",
                description="11 قابلیت تکمیلی - ابزارهای پیشرفته",
                input_message_content=InputTextMessageContent(
                    message_text="<b>🎛 پنل مدیریت سلف</b>\n\n💡 <i>صفحه دوم - 11 قابلیت تکمیلی</i>",
                    parse_mode='HTML'
                ),
                reply_markup=get_main_menu_page2(user_id)
            )
        ]
        await update.inline_query.answer(results, cache_time=300, is_personal=True)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if not f"_{user_id}" in data:
        await query.answer("❌ دسترسی غیرمجاز!", show_alert=True)
        return
    
    parts = data.split("_")
    
    if len(parts) >= 2:
        action = parts[0]
        if parts[0] == "help" and parts[1] == "back":
            action = "help_back"
            page = int(parts[2]) if len(parts) > 2 else 1
        elif parts[0] == "clock" and parts[1] == "back":
            action = "clock_back"
            page = int(parts[2]) if len(parts) > 2 else 1
        elif parts[0] == "oneclick" and parts[1] == "back":
            action = "oneclick_back"
            page = int(parts[2]) if len(parts) > 2 else 1
        else:
            page = int(parts[-1]) if parts[-1].isdigit() else 1
    else:
        action = parts[0]
        page = 1
    
    if action == "help" and parts[1] == "oneclick":
        text = HELP_TEXTS["oneclick"] + """
        
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 زیرمجموعه‌ها:

روی دکمه‌های زیر کلیک کنید.
"""
        try:
            await query.edit_message_text(
                text,
                reply_markup=get_oneclick_buttons(user_id, page),
                parse_mode='HTML'
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "oneclick" and parts[1] == "time":
        text = HELP_TEXTS["time"] + """
        
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ مدیریت ساعت:

وضعیت فعلی را مشاهده و تنظیم کنید.
"""
        try:
            await query.edit_message_text(
                text,
                reply_markup=get_clock_buttons(user_id, page),
                parse_mode='HTML'
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "oneclick" and parts[1] == "format":
        text = HELP_TEXTS["format"] + """
        
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ مدیریت فرمت‌ها:

روی هر دکمه کلیک کنید تا فعال/غیرفعال شود.
✅ = فعال | ⬜ = غیرفعال
"""
        try:
            await query.edit_message_text(
                text,
                reply_markup=get_format_buttons(user_id, page),
                parse_mode='HTML'
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "oneclick_back":
        text = HELP_TEXTS["oneclick"] + """
        
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 زیرمجموعه‌ها:

روی دکمه‌های زیر کلیک کنید.
"""
        try:
            await query.edit_message_text(
                text,
                reply_markup=get_oneclick_buttons(user_id, page),
                parse_mode='HTML'
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "help" and parts[1] == "time":
        text = HELP_TEXTS["time"] + """
        
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ اجرای سریع:

روی دکمه‌های زیر کلیک کنید.
"""
        try:
            await query.edit_message_text(
                text,
                reply_markup=get_clock_buttons(user_id, page),
                parse_mode='HTML'
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "help" and parts[1] == "fonts":
        try:
            await query.edit_message_text(
                "🔤 <b>فونت مورد نظر را انتخاب کنید</b>",
                reply_markup=get_font_buttons(user_id, page),
                parse_mode='HTML'
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "time":
        if len(parts) > 1 and parts[1] == "on":
            send_command_to_self_bot("تایم روشن", user_id)
            
            settings = load_settings()
            settings['time_status'] = 'روشن'
            save_settings(settings)
            
            try:
                await query.edit_message_text(
                    "✅ <b>ساعت روشن شد</b>\n\n"
                    "⏰ زمان کنار نام شما نمایش داده می‌شود\n"
                    "🔄 هر دقیقه آپدیت می‌شود",
                    reply_markup=get_clock_buttons(user_id, page),
                    parse_mode='HTML'
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"Error: {e}")
        elif len(parts) > 1 and parts[1] == "off":
            send_command_to_self_bot("تایم خاموش", user_id)
            
            settings = load_settings()
            settings['time_status'] = 'خاموش'
            save_settings(settings)
            
            try:
                await query.edit_message_text(
                    "✅ <b>ساعت خاموش شد</b>\n\n"
                    "⏰ زمان کنار نام شما حذف شد",
                    reply_markup=get_clock_buttons(user_id, page),
                    parse_mode='HTML'
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"Error: {e}")
        return
    
    if action == "font":
        if len(parts) > 1:
            font_num = parts[1]
            send_command_to_self_bot(f"تنظیم فونت {font_num}", user_id)
            
            settings = load_settings()
            settings['font'] = int(font_num)
            save_settings(settings)
            
            try:
                await query.edit_message_text(
                    f"✅ <b>فونت {font_num} تنظیم شد</b>\n\n"
                    f"🔤 {get_font_preview(int(font_num))}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت به ساعت", callback_data=f"clock_back_{user_id}_{page}")]
                    ]),
                    parse_mode='HTML'
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"Error: {e}")
        return
    
    if action == "format":
        if len(parts) > 1:
            format_key = parts[1]
            
            if format_key == "reset":
                send_command_to_self_bot("فرمت ریست", user_id)
                
                settings = load_settings()
                settings['formats'] = {}
                save_settings(settings)
                
                try:
                    await query.edit_message_text(
                        "✅ همه فرمت‌ها ریست شدند",
                        reply_markup=get_format_buttons(user_id, page),
                        parse_mode='HTML'
                    )
                except Exception as e:
                    if "Message is not modified" not in str(e):
                        print(f"Error: {e}")
                return
            
            if format_key == "status":
                send_command_to_self_bot("فرمت وضعیت", user_id)
                await asyncio.sleep(2)
                
                if os.path.exists(REACTION_RESULT_FILE):
                    try:
                        with open(REACTION_RESULT_FILE, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            result = data.get('result', '')
                            await query.edit_message_text(
                                result,
                                reply_markup=get_format_buttons(user_id, page),
                                parse_mode='HTML'
                            )
                    except:
                        await query.edit_message_text(
                            "📊 وضعیت فرمت‌ها:\n\nدریافت نشد",
                            reply_markup=get_format_buttons(user_id, page),
                            parse_mode='HTML'
                        )
                return
            
            format_names = {
                "bold": "بولد",
                "italic": "ایتالیک",
                "underline": "زیرخط",
                "strike": "خط خورده",
                "spoiler": "اسپویلر",
                "code": "کد",
                "pre": "پیش‌فرمت",
                "quote": "نقل‌قول"
            }
            
            if format_key in format_names:
                settings = load_settings()
                if 'formats' not in settings:
                    settings['formats'] = {}
                
                current = settings['formats'].get(format_key, False)
                settings['formats'][format_key] = not current
                
                persian_name = format_names[format_key]
                action_text = "روشن" if not current else "خاموش"
                send_command_to_self_bot(f"فرمت {persian_name} {action_text}", user_id)
                
                save_settings(settings)
                
                try:
                    await query.edit_message_text(
                        f"✅ فرمت {persian_name} {'فعال' if not current else 'غیرفعال'} شد",
                        reply_markup=get_format_buttons(user_id, page),
                        parse_mode='HTML'
                    )
                except Exception as e:
                    if "Message is not modified" not in str(e):
                        print(f"Error: {e}")
                return
    
    if action == "clock_back":
        text = HELP_TEXTS["time"] + """
        
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ اجرای سریع:

روی دکمه‌های زیر کلیک کنید.
"""
        try:
            await query.edit_message_text(
                text,
                reply_markup=get_clock_buttons(user_id, page),
                parse_mode='HTML'
            )
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "help_back":
        if page == 1:
            text = "<b>🎛 پنل مدیریت سلف</b>\n\n💡 صفحه اول"
            try:
                await query.edit_message_text(text, reply_markup=get_main_menu_page1(user_id), parse_mode='HTML')
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"Error: {e}")
        else:
            text = "<b>🎛 پنل مدیریت سلف</b>\n\n💡 صفحه دوم"
            try:
                await query.edit_message_text(text, reply_markup=get_main_menu_page2(user_id), parse_mode='HTML')
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"Error: {e}")
        return
    
    if action == "page1":
        text = "<b>🎛 پنل مدیریت سلف</b>\n\n💡 صفحه اول"
        try:
            await query.edit_message_text(text, reply_markup=get_main_menu_page1(user_id), parse_mode='HTML')
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "page2":
        text = "<b>🎛 پنل مدیریت سلف</b>\n\n💡 صفحه دوم"
        try:
            await query.edit_message_text(text, reply_markup=get_main_menu_page2(user_id), parse_mode='HTML')
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "close":
        try:
            await query.edit_message_text("✅ پنل بسته شد")
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "reopen":
        text = "<b>🎛 پنل مدیریت سلف</b>\n\n💡 صفحه اول"
        try:
            await query.edit_message_text(text, reply_markup=get_main_menu_page1(user_id), parse_mode='HTML')
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error: {e}")
        return
    
    if action == "help":
        if len(parts) > 1 and parts[1] in HELP_TEXTS:
            text = HELP_TEXTS.get(parts[1], "راهنما")
            try:
                await query.edit_message_text(text, reply_markup=get_back_button(user_id, page), parse_mode='HTML')
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"Error: {e}")
        return
    
    await query.answer("⏳ در حال آماده‌سازی...", show_alert=True)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

def main():
    if not TOKEN or TOKEN == "توکن_هلپر_را_در_متغیر_HELPER_TOKEN_بگذار":
        raise SystemExit("HELPER_TOKEN را در متغیرهای محیطی تنظیم کنید.")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, show_menu))
    app.add_handler(InlineQueryHandler(handle_inline_query))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)
    
    print("🤖 ربات هلپر اجرا شد")
    app.run_polling()

if __name__ == "__main__":
    main()