import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import asyncio
import time
import secrets
import os
import subprocess
import sys
import sqlite3
import random
from datetime import datetime

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# حالت‌های مکالمه
CHECK_MEMBERSHIP, ACTIVATION_PANEL, COIN_PURCHASE, CONFIRM_PURCHASE = range(4)

class TelegramAuthBot:
    def __init__(self, token, admin_id, channel, channel_url):
        self.token = token
        self.channel_username = channel.strip()
        self.channel_url = channel_url.strip()
        self.application = Application.builder().token(token).build()
        self.user_sessions = {}
        self.user_coins = {}
        self.active_selfbots = {}
        self.invite_links = {}
        self.user_referrals = {}
        self.user_first_start = {}
        self.active_bets = {}  # اضافه شد
        self.group_bets = {}   # اضافه شد
        self.owner_id = int(admin_id)
        
        # دیتابیس کاربران
        self.init_users_db()
        
        self.user_coins[self.owner_id] = 999999999
        self.setup_handlers()
    
    def init_users_db(self):
        """ایجاد دیتابیس کاربران"""
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            coins INTEGER DEFAULT 0,
            invited_by INTEGER,
            join_date TEXT,
            is_active INTEGER DEFAULT 1
        )''')
        conn.commit()
        conn.close()
    
    def setup_handlers(self):
        # ابتدا هندلرهای معمولی
        self.application.add_handler(CommandHandler("bet", self.create_bet))
        self.application.add_handler(CommandHandler("gbet", self.create_group_bet))
        self.application.add_handler(CommandHandler("link", self.create_invite_link))
        self.application.add_handler(CommandHandler("balance", self.show_balance))
        self.application.add_handler(CommandHandler("transfer", self.transfer_coins))
        
        # دستورات مالک
        self.application.add_handler(CommandHandler("kasr", self.kasr_coins))
        self.application.add_handler(CommandHandler("id", self.get_user_id))
        self.application.add_handler(CommandHandler("addcoins", self.add_coins))
        
        # هندلر برای پیام‌های متنی
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^انتقال\s+\d+$'), self.transfer_coins_farsi))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^موجودی$'), self.show_balance_farsi))
        
        # هندلر برای شرط‌بندی
        self.application.add_handler(CallbackQueryHandler(self.join_bet, pattern='^join_bet_'))
        self.application.add_handler(CallbackQueryHandler(self.join_group_bet, pattern='^join_gbet_'))
        self.application.add_handler(CallbackQueryHandler(self.cancel_group_bet, pattern='^cancel_gbet_'))
        
        # در آخر Conversation Handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                CHECK_MEMBERSHIP: [
                    CallbackQueryHandler(self.check_membership, pattern='^(check|join)$')
                ],
                ACTIVATION_PANEL: [
                    CallbackQueryHandler(self.activation_panel, pattern='^(activate|support|buy_coins|back|stats|invite)$')
                ],
                COIN_PURCHASE: [
                    CallbackQueryHandler(self.coin_purchase, pattern='^.*$')
                ],
                CONFIRM_PURCHASE: [
                    CallbackQueryHandler(self.confirm_purchase, pattern='^(confirm_purchase|cancel_purchase)$')
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            per_message=False
        )
        
        self.application.add_handler(conv_handler)
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == self.owner_id
    
    def create_welcome_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("📥 پیوستن", url=self.channel_url),
                InlineKeyboardButton("✅ بررسی", callback_data="check")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_activation_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("🚀 فعال سازی سلف", callback_data="activate"),
                InlineKeyboardButton("💰 خرید سکه", callback_data="buy_coins")
            ],
            [
                InlineKeyboardButton("📊 آمار و موجودی", callback_data="stats"),
                InlineKeyboardButton("🎫 لینک دعوت", callback_data="invite")
            ],
            [
                InlineKeyboardButton("🛟 پشتیبانی", url="https://t.me/KHAN_Sohail_580")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_stats_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("💳 افزایش موجودی", callback_data="buy_coins"),
                InlineKeyboardButton("🎫 لینک دعوت", callback_data="invite")
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data="back")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_invite_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("📊 آمار دعوت", callback_data="stats"),
                InlineKeyboardButton("💳 خرید سکه", callback_data="buy_coins")
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data="back")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_coin_keyboard(self, current_amount=""):
        display_amount = current_amount if current_amount else "0"
        
        keyboard = [
            [InlineKeyboardButton(f"💌 تعداد سکه: {display_amount}", callback_data="display_coins")],
            [
                InlineKeyboardButton("1", callback_data="coin_1"),
                InlineKeyboardButton("2", callback_data="coin_2"),
                InlineKeyboardButton("3", callback_data="coin_3")
            ],
            [
                InlineKeyboardButton("4", callback_data="coin_4"),
                InlineKeyboardButton("5", callback_data="coin_5"),
                InlineKeyboardButton("6", callback_data="coin_6")
            ],
            [
                InlineKeyboardButton("7", callback_data="coin_7"),
                InlineKeyboardButton("8", callback_data="coin_8"),
                InlineKeyboardButton("9", callback_data="coin_9")
            ],
            [
                InlineKeyboardButton("🗑️ حذف", callback_data="coin_delete"),
                InlineKeyboardButton("0", callback_data="coin_0"),
                InlineKeyboardButton("✅ تایید", callback_data="coin_submit")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_purchase_confirmation_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("✅ تأیید خرید", callback_data="confirm_purchase"),
                InlineKeyboardButton("❌ انصراف", callback_data="cancel_purchase")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_bet_keyboard(self, bet_id):
        keyboard = [
            [
                InlineKeyboardButton("🎰 پیوستن به شرط", callback_data=f"join_bet_{bet_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_group_bet_keyboard(self, bet_id):
        keyboard = [
            [
                InlineKeyboardButton("🎰 پیوستن به شرط", callback_data=f"join_gbet_{bet_id}"),
                InlineKeyboardButton("❌ لغو شرط", callback_data=f"cancel_gbet_{bet_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if self.is_owner(user_id):
            self.user_coins[user_id] = 999999999
        
        # بررسی لینک دعوت
        if context.args and len(context.args) > 0:
            invite_code = context.args[0]
            if invite_code in self.invite_links:
                referrer_id = self.invite_links[invite_code]
                
                # اهدای 7 سکه به دعوت کننده
                if referrer_id not in self.user_coins:
                    self.user_coins[referrer_id] = 0
                self.user_coins[referrer_id] += 7
                
                # ذخیره اطلاعات دعوت شونده
                if referrer_id not in self.user_referrals:
                    self.user_referrals[referrer_id] = []
                self.user_referrals[referrer_id].append(user_id)
                
                # اطلاع به دعوت کننده
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 کاربر جدیدی با لینک دعوت شما وارد ربات شد!\n💰 7 سکه به عنوان پاداش دریافت کردید!"
                    )
                except:
                    pass
        
        # هدیه اولیه برای کاربران جدید
        if user_id not in self.user_first_start and not self.is_owner(user_id):
            self.user_first_start[user_id] = True
            if user_id not in self.user_coins:
                self.user_coins[user_id] = 3
                await update.message.reply_text(
                    "🎁 **هدیه ویژه!**\n\n"
                    "به شما 3 سکه رایگان هدیه داده شد!\n"
                    "💰 موجودی فعلی: 3 سکه"
                )
        
        welcome_text = (
            "🌐 𝙅𝙤𝙞𝙣 𝙊𝙪𝙧 𝘾𝙝𝙖𝙣𝙣𝙚𝙡 💫\n\n"
            "Before using the bot, make sure you've joined our official channel 💎\n"
            "👉 𝚃𝚊𝚙 𝚃𝚘 𝙹𝚘𝚞𝚛𝚗: [@Sourrce_kade]\n"
            "🚀 After joining, come back and tap \"✅ بررسی\""
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.create_welcome_keyboard(),
            parse_mode='Markdown'
        )
        return CHECK_MEMBERSHIP
    
    async def check_membership(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if query.data == "join":
            await query.edit_message_text(
                "📥 ابتدا عضو کانال شوید و سپس بررسی را بزنید.",
                reply_markup=self.create_welcome_keyboard()
            )
            return CHECK_MEMBERSHIP
        await query.edit_message_text("🔍 در حال بررسی عضویت شما...")
        try:
            member = await context.bot.get_chat_member(chat_id=self.channel_username, user_id=user_id)
            if member.status in ("member", "administrator", "creator") or (member.status == "restricted" and getattr(member, "is_member", False)):
                await query.edit_message_text(
                    "🎉 عضویت شما تأیید شد!\n\nپنل اصلی:",
                    reply_markup=self.create_activation_keyboard()
                )
                return ACTIVATION_PANEL
            await query.edit_message_text(
                "❌ هنوز عضو کانال نیستید. ابتدا عضو شوید و دوباره بررسی کنید.",
                reply_markup=self.create_welcome_keyboard()
            )
        except Exception as e:
            logging.exception("Membership check failed: %s", e)
            await query.edit_message_text(
                "❌ بررسی عضویت انجام نشد. مطمئن شوید ربات در کانال ادمین است و شناسه کانال درست تنظیم شده.",
                reply_markup=self.create_welcome_keyboard()
            )
        return CHECK_MEMBERSHIP

    async def activation_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "activate":
            await query.edit_message_text(
                "ℹ️ این نسخه فقط امکانات امن ربات را از طریق Bot API ارائه می‌کند.\n\n"
                "برای امنیت حساب، شماره تلفن، کد ورود، رمز دومرحله‌ای یا Session تلگرام از شما دریافت نمی‌شود.\n"
                "امکانات موجودی، دعوت، انتقال سکه و شرط‌بندی از منوی دستورات قابل استفاده‌اند.",
                reply_markup=self.create_activation_keyboard()
            )
            return ACTIVATION_PANEL
        
        elif query.data == "buy_coins":
            coin_text = (
                "💌•••خرید سکه(کوین)•••💌\n\n"
                "💰 هر عدد سکه: 200 تومن\n"
                "‼️ 𝐂𝐨𝐢𝐧 ➜ تعداد سکه مورد نظر خود را وارد کنید\n\n"
                "⌨️ از کیبورد زیر برای وارد کردن تعداد سکه استفاده کنید:"
            )
            
            await query.edit_message_text(
                coin_text,
                reply_markup=self.create_coin_keyboard()
            )
            return COIN_PURCHASE
        
        elif query.data == "stats":
            await self.show_stats_panel(query)
            return ACTIVATION_PANEL
        
        elif query.data == "invite":
            await self.show_invite_panel(query, context)
            return ACTIVATION_PANEL
        
        elif query.data == "support":
            await query.edit_message_text(
                "🛟 در حال انتقال به پشتیبانی...",
                reply_markup=self.create_activation_keyboard()
            )
            return ACTIVATION_PANEL
        
        elif query.data == "back":
            activation_text = (
                "💡 𝐒𝐞𝐭 𝐘𝐨𝐮𝐫 𝐒𝐞𝐥𝐟 𝐀𝐜𝐭𝐢𝐯𝐞 🔋\n\n"
                "Activate your own self from the menu below 👇\n"
                "🚀 One tap away from your smart control panel ⚙️"
            )
            
            await query.edit_message_text(
                activation_text,
                reply_markup=self.create_activation_keyboard()
            )
            return ACTIVATION_PANEL
    
    async def show_stats_panel(self, query):
        """نمایش پنل آمار و موجودی"""
        user_id = query.from_user.id
        user_coins = self.user_coins.get(user_id, 0)
        total_value = user_coins * 200
        referrals_count = len(self.user_referrals.get(user_id, []))
        
        stats_text = (
            f"📊 **آمار و موجودی شما**\n\n"
            f"💰 **موجودی سکه:** {user_coins} سکه\n"
            f"💎 **ارزش ریالی:** {total_value:,} تومن\n"
            f"👥 **تعداد دعوت‌ها:** {referrals_count} نفر\n"
            f"🎁 **سکه از دعوت:** {referrals_count * 7} سکه\n\n"
            f"💡 **نکته:** به ازای هر دعوت موفق 7 سکه پاداش دریافت می‌کنید!"
        )
        
        await query.edit_message_text(
            stats_text,
            reply_markup=self.create_stats_keyboard()
        )
    
    async def show_invite_panel(self, query, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل لینک دعوت"""
        user_id = query.from_user.id
        username = query.from_user.username or f"user_{user_id}"
        
        invite_code = secrets.token_urlsafe(8)
        self.invite_links[invite_code] = user_id
        
        invite_link = f"https://t.me/{context.bot.username}?start={invite_code}"
        referrals_count = len(self.user_referrals.get(user_id, []))
        
        invite_text = (
            f"🎫 **لینک دعوت شما**\n\n"
            f"🔗 **لینک:** `{invite_link}`\n\n"
            f"💎 **مزایای دعوت:**\n"
            f"• به ازای هر دعوت: **7 سکه** پاداش\n"
            f"• دعوت شده: **3 سکه** هدیه اولیه\n"
            f"• بدون محدودیت تعداد دعوت\n\n"
            f"📊 **آمار دعوت‌های شما:** {referrals_count} نفر\n"
            f"💰 **سکه‌های کسب شده:** {referrals_count * 7} سکه"
        )
        
        await query.edit_message_text(
            invite_text,
            reply_markup=self.create_invite_keyboard(),
            parse_mode='Markdown'
        )
    
    async def coin_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if 'coin_amount' not in context.user_data:
            context.user_data['coin_amount'] = ''
        
        coin_amount = context.user_data['coin_amount']
        
        if query.data == "coin_delete":
            context.user_data['coin_amount'] = ''
            await query.edit_message_text(
                "🗑️ تعداد سکه پاک شد.\nلطفاً تعداد سکه مورد نظر را وارد کنید:",
                reply_markup=self.create_coin_keyboard()
            )
            return COIN_PURCHASE
        
        elif query.data == "coin_submit":
            if not coin_amount or int(coin_amount) <= 0:
                await query.edit_message_text(
                    "❌ لطفاً تعداد سکه معتبر وارد کنید!",
                    reply_markup=self.create_coin_keyboard(coin_amount)
                )
                return COIN_PURCHASE
            
            coin_count = int(coin_amount)
            total_price = coin_count * 200
            
            purchase_text = (
                f"💌••• تأیید خرید سکه •••💌\n\n"
                f"🩸 𝐌𝐨𝐧𝐞𝐲 ➜ {total_price:,} تومن\n"
                f"💌 𝐂𝐨𝐢𝐧 ➜ {coin_count} سکه\n\n"
                f"       𝟼𝟷𝟶𝟺 𝟹𝟹𝟽𝟿 𝟻𝟸𝟶𝟺 𝟼𝟽𝟹𝟼\n\n"
                f"😘 کاربر گرامی برای خرید ابتدا مبلغ تعیین شده رو به شماره کارت بالا انتقال داده سپس عکس از رسید را برای مالک سلف ارسال کنید ❤️‍🩹 @sinyoremad"
            )
            
            await query.edit_message_text(purchase_text)
            
            context.user_data['coin_amount'] = ''
            return ConversationHandler.END
        
        elif query.data.startswith("coin_"):
            digit = query.data.split("_")[1]
            context.user_data['coin_amount'] += digit
            
            updated_amount = context.user_data['coin_amount']
            await query.edit_message_text(
                f"💌 تعداد سکه: {updated_amount}\n\n"
                f"💰 مبلغ قابل پرداخت: {int(updated_amount or 0) * 200:,} تومن\n\n"
                f"⌨️ از کیبورد زیر برای ادامه استفاده کنید:",
                reply_markup=self.create_coin_keyboard(updated_amount)
            )
            return COIN_PURCHASE
        
        elif query.data == "display_coins":
            await query.answer(f"تعداد سکه فعلی: {coin_amount or '0'}")
            return COIN_PURCHASE
    
    async def confirm_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "confirm_purchase":
            coin_amount = context.user_data.get('coin_amount', '0')
            coin_count = int(coin_amount)
            total_price = coin_count * 200
            
            if user_id not in self.user_coins:
                self.user_coins[user_id] = 0
            self.user_coins[user_id] += coin_count
            
            final_purchase_text = (
                f"💌••• تأیید خرید سکه •••💌\n\n"
                f"🩸 𝐌𝐨𝐧𝐞𝐲 ➜ {total_price:,} تومن\n"
                f"💌 𝐂𝐨𝐢𝐧 ➜ {coin_count} سکه\n\n"
                f"       𝟼𝟷𝟶𝟺 𝟹𝟹𝟽𝟿 𝟻𝟸𝟶𝟺 𝟼𝟽𝟹𝟼\n\n"
                f"😘 کاربر گرامی برای خرید ابتدا مبلغ تعیین شده رو به شماره کارت بالا انتقال داده سپس عکس از رسید را برای مالک سلف ارسال کنید ❤️‍🩹 @sinyoremad"
            )
            
            await query.edit_message_text(final_purchase_text)
            
            context.user_data['coin_amount'] = ''
            return ConversationHandler.END
        
        elif query.data == "cancel_purchase":
            context.user_data['coin_amount'] = ''
            
            await query.edit_message_text(
                "❌ خرید لغو شد.\n\n"
                "💌•••خرید سکه(کوین)•••💌\n\n"
                "💰 هر عدد سکه: 200 تومن\n"
                "‼️ 𝐂𝐨𝐢𝐧 ➜ تعداد سکه مورد نظر خود را وارد کنید",
                reply_markup=self.create_coin_keyboard()
            )
            return COIN_PURCHASE
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ عملیات لغو شد. برای شروع دوباره /start را بزنید.")
        return ConversationHandler.END
    
    async def create_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ایجاد شرط‌بندی جدید"""
        user_id = update.message.from_user.id
        username = update.message.from_user.username or f"user_{user_id}"
        
        if not context.args:
            await update.message.reply_text(
                "❌ لطفاً تعداد سکه شرط را مشخص کنید:\n"
                "مثال: `/bet 10`"
            )
            return
        
        try:
            coin_amount = int(context.args[0])
            if coin_amount <= 0:
                await update.message.reply_text("❌ تعداد سکه باید بیشتر از صفر باشد!")
                return
            
            if user_id not in self.user_coins or self.user_coins[user_id] < coin_amount:
                await update.message.reply_text(
                    f"❌ موجودی سکه شما کافی نیست!\n"
                    f"💰 موجودی فعلی: {self.user_coins.get(user_id, 0)} سکه\n"
                    f"💸 سکه مورد نیاز: {coin_amount} سکه"
                )
                return
            
            bet_id = str(int(time.time()))
            self.active_bets[bet_id] = {
                'creator_id': user_id,
                'creator_username': username,
                'coin_amount': coin_amount,
                'participants': [user_id],
                'message_id': None
            }
            
            self.user_coins[user_id] -= coin_amount
            
            bet_text = (
                f"🎰●شرط بندی ساخته شده●🎰\n\n"
                f"👤 ساخته شده توسط: @{username}\n"
                f"💌 تعداد کوین: {coin_amount} سکه\n"
                f"💰 مبلغ به قیمت: {coin_amount * 200:,} تومن"
            )
            
            message = await update.message.reply_text(
                bet_text,
                reply_markup=self.create_bet_keyboard(bet_id)
            )
            
            self.active_bets[bet_id]['message_id'] = message.message_id
            
            await update.message.reply_text(
                f"✅ شرط‌بندی با موفقیت ایجاد شد!\n"
                f"💎 {coin_amount} سکه شما بلوکه شد.\n"
                f"⏳ منتظر شرکت کننده دوم باشید..."
            )
            
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
    
    async def create_group_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ایجاد شرط‌بندی گروهی"""
        user_id = update.message.from_user.id
        username = update.message.from_user.username or f"user_{user_id}"
        chat_id = update.message.chat_id
        
        # بررسی اینکه آیا در گروه هستیم
        if update.message.chat.type == 'private':
            await update.message.reply_text(
                "❌ این دستور فقط در گروه‌ها قابل استفاده است!\n"
                "لطفاً در یک گروه این دستور را ارسال کنید."
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ لطفاً تعداد سکه شرط را مشخص کنید:\n"
                "مثال: `/gbet 10`"
            )
            return
        
        try:
            coin_amount = int(context.args[0])
            if coin_amount <= 0:
                await update.message.reply_text("❌ تعداد سکه باید بیشتر از صفر باشد!")
                return
            
            if user_id not in self.user_coins or self.user_coins[user_id] < coin_amount:
                await update.message.reply_text(
                    f"❌ موجودی سکه شما کافی نیست!\n"
                    f"💰 موجودی فعلی: {self.user_coins.get(user_id, 0)} سکه\n"
                    f"💸 سکه مورد نیاز: {coin_amount} سکه"
                )
                return
            
            bet_id = str(int(time.time()))
            self.group_bets[bet_id] = {
                'creator_id': user_id,
                'creator_username': username,
                'chat_id': chat_id,
                'coin_amount': coin_amount,
                'participants': [user_id],
                'message_id': None,
                'created_at': time.time()
            }
            
            self.user_coins[user_id] -= coin_amount
            
            bet_text = (
                f"🎰●شرط بندی گروهی●🎰\n\n"
                f"👤 سازنده: @{username}\n"
                f"💌 تعداد کوین: {coin_amount} سکه\n"
                f"💰 مبلغ: {coin_amount * 200:,} تومن\n"
                f"👥 شرکت‌کنندگان: 1 نفر\n\n"
                f"⏰ زمان باقی‌مانده: 5 دقیقه"
            )
            
            message = await update.message.reply_text(
                bet_text,
                reply_markup=self.create_group_bet_keyboard(bet_id)
            )
            
            self.group_bets[bet_id]['message_id'] = message.message_id
            
            # زمان‌بندی برای پایان شرط
            asyncio.create_task(self.finish_group_bet(bet_id, context))
            
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
    
    async def finish_group_bet(self, bet_id: str, context: ContextTypes.DEFAULT_TYPE):
        """پایان دادن به شرط‌بندی گروهی پس از 5 دقیقه"""
        await asyncio.sleep(300)  # 5 دقیقه
        
        if bet_id not in self.group_bets:
            return
        
        bet = self.group_bets[bet_id]
        
        if len(bet['participants']) < 2:
            # بازگشت سکه‌ها به سازنده
            if bet['creator_id'] in self.user_coins:
                self.user_coins[bet['creator_id']] += bet['coin_amount']
            
            try:
                await context.bot.edit_message_text(
                    chat_id=bet['chat_id'],
                    message_id=bet['message_id'],
                    text=(
                        f"❌ شرط‌بندی گروهی لغو شد!\n\n"
                        f"👤 سازنده: @{bet['creator_username']}\n"
                        f"💌 تعداد کوین: {bet['coin_amount']} سکه\n"
                        f"💰 علت: تعداد شرکت‌کنندگان کافی نبود\n"
                        f"💎 سکه‌ها به حساب سازنده بازگردانده شد."
                    )
                )
            except:
                pass
            
            del self.group_bets[bet_id]
            return
        
        # انتخاب برنده
        winner_id = random.choice(bet['participants'])
        total_coins = bet['coin_amount'] * len(bet['participants'])
        
        if winner_id not in self.user_coins:
            self.user_coins[winner_id] = 0
        self.user_coins[winner_id] += total_coins
        
        # پیدا کردن نام برنده
        winner_username = bet['creator_username'] if winner_id == bet['creator_id'] else "یکی از شرکت‌کنندگان"
        
        result_text = (
            f"🎲شرط بندی گروهی انجام شد🎮\n\n"
            f"🏆 برنده: @{winner_username}\n"
            f"👥 تعداد شرکت‌کنندگان: {len(bet['participants'])} نفر\n"
            f"🪙 مجموع جوایز: {total_coins} سکه\n"
            f"💰 ارزش: {total_coins * 200:,} تومن\n"
            f"🔮 ساعت: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        try:
            await context.bot.edit_message_text(
                chat_id=bet['chat_id'],
                message_id=bet['message_id'],
                text=result_text
            )
        except:
            pass
        
        # اطلاع به برنده
        try:
            await context.bot.send_message(
                chat_id=winner_id,
                text=f"🎉 شما در شرط‌بندی گروهی برنده شدید!\n💰 {total_coins} سکه به حساب شما اضافه شد!"
            )
        except:
            pass
        
        del self.group_bets[bet_id]
    
    async def join_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        username = query.from_user.username or f"user_{user_id}"
        bet_id = query.data.replace('join_bet_', '')
        
        if bet_id not in self.active_bets:
            await query.edit_message_text("❌ این شرط‌بندی منقضی شده است!")
            return
        
        bet = self.active_bets[bet_id]
        
        if user_id == bet['creator_id']:
            await query.answer("❌ شما سازنده این شرط هستید!", show_alert=True)
            return
        
        if user_id in bet['participants']:
            await query.answer("❌ شما قبلاً در این شرط شرکت کرده‌اید!", show_alert=True)
            return
        
        if user_id not in self.user_coins or self.user_coins[user_id] < bet['coin_amount']:
            await query.answer(
                f"❌ موجودی سکه شما کافی نیست!\n"
                f"💰 موجودی مورد نیاز: {bet['coin_amount']} سکه",
                show_alert=True
            )
            return
        
        bet['participants'].append(user_id)
        self.user_coins[user_id] -= bet['coin_amount']
        
        winner_id = random.choice(bet['participants'])
        loser_id = bet['creator_id'] if winner_id != bet['creator_id'] else user_id
        
        winner_username = bet['creator_username'] if winner_id == bet['creator_id'] else username
        loser_username = username if winner_id == bet['creator_id'] else bet['creator_username']
        
        total_coins = bet['coin_amount'] * 2
        if winner_id not in self.user_coins:
            self.user_coins[winner_id] = 0
        self.user_coins[winner_id] += total_coins
        
        del self.active_bets[bet_id]
        
        result_text = (
            f"🎲شرط بندی انجام شد🎮\n\n"
            f"🏆 برنده: @{winner_username}\n"
            f"🥀 بازنده: @{loser_username}\n"
            f"🪙 کوین: {total_coins} سکه\n"
            f"🔮 ساعت: {datetime.now().strftime('%H:%M:%S')}\n"
            f"🌋 مبلغ: {total_coins * 200:,} تومن"
        )
        
        await query.edit_message_text(result_text)
        
        try:
            await context.bot.send_message(
                chat_id=winner_id,
                text=f"🎉 شما در شرط‌بندی برنده شدید!\n💰 {total_coins} سکه به حساب شما اضافه شد!"
            )
        except:
            pass
        
        try:
            await context.bot.send_message(
                chat_id=loser_id,
                text=f"💔 متأسفانه در شرط‌بندی بازنده شدید.\n💎 {bet['coin_amount']} سکه از حساب شما کسر شد."
            )
        except:
            pass
    
    async def join_group_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        username = query.from_user.username or f"user_{user_id}"
        bet_id = query.data.replace('join_gbet_', '')
        
        if bet_id not in self.group_bets:
            await query.answer("❌ این شرط‌بندی منقضی شده است!", show_alert=True)
            return
        
        bet = self.group_bets[bet_id]
        
        if user_id in bet['participants']:
            await query.answer("❌ شما قبلاً در این شرط شرکت کرده‌اید!", show_alert=True)
            return
        
        if user_id not in self.user_coins or self.user_coins[user_id] < bet['coin_amount']:
            await query.answer(
                f"❌ موجودی سکه شما کافی نیست!\n"
                f"💰 موجودی مورد نیاز: {bet['coin_amount']} سکه",
                show_alert=True
            )
            return
        
        bet['participants'].append(user_id)
        self.user_coins[user_id] -= bet['coin_amount']
        
        remaining_time = 300 - (time.time() - bet['created_at'])
        minutes = int(remaining_time // 60)
        seconds = int(remaining_time % 60)
        
        updated_text = (
            f"🎰●شرط بندی گروهی●🎰\n\n"
            f"👤 سازنده: @{bet['creator_username']}\n"
            f"💌 تعداد کوین: {bet['coin_amount']} سکه\n"
            f"💰 مبلغ: {bet['coin_amount'] * 200:,} تومن\n"
            f"👥 شرکت‌کنندگان: {len(bet['participants'])} نفر\n\n"
            f"⏰ زمان باقی‌مانده: {minutes:02d}:{seconds:02d}"
        )
        
        await query.edit_message_text(
            updated_text,
            reply_markup=self.create_group_bet_keyboard(bet_id)
        )
        
        await query.answer(f"✅ شما با موفقیت به شرط پیوستید! {bet['coin_amount']} سکه از حساب شما کسر شد.")
    
    async def cancel_group_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        bet_id = query.data.replace('cancel_gbet_', '')
        
        if bet_id not in self.group_bets:
            await query.answer("❌ این شرط‌بندی منقضی شده است!", show_alert=True)
            return
        
        bet = self.group_bets[bet_id]
        
        if user_id != bet['creator_id']:
            await query.answer("❌ فقط سازنده شرط می‌تواند آن را لغو کند!", show_alert=True)
            return
        
        # بازگشت سکه‌ها به همه شرکت‌کنندگان
        for participant_id in bet['participants']:
            if participant_id in self.user_coins:
                self.user_coins[participant_id] += bet['coin_amount']
        
        await query.edit_message_text(
            f"❌ شرط‌بندی گروهی توسط سازنده لغو شد!\n\n"
            f"💌 تعداد کوین: {bet['coin_amount']} سکه\n"
            f"👥 شرکت‌کنندگان: {len(bet['participants'])} نفر\n"
            f"💎 سکه‌ها به حساب همه بازگردانده شد."
        )
        
        del self.group_bets[bet_id]
    
    async def create_invite_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        username = update.message.from_user.username or f"user_{user_id}"
        
        invite_code = secrets.token_urlsafe(8)
        self.invite_links[invite_code] = user_id
        
        invite_link = f"https://t.me/{context.bot.username}?start={invite_code}"
        referrals_count = len(self.user_referrals.get(user_id, []))
        
        invite_text = (
            f"🎫 **لینک دعوت شما**\n\n"
            f"🔗 لینک: `{invite_link}`\n\n"
            f"💎 **مزایا:**\n"
            f"• به ازای هر دعوت: **7 سکه** پاداش\n"
            f"• دعوت شده: **3 سکه** هدیه اولیه\n"
            f"• بدون محدودیت تعداد دعوت\n\n"
            f"📊 آمار دعوت‌های شما: {referrals_count} نفر\n"
            f"💰 سکه‌های کسب شده: {referrals_count * 7} سکه"
        )
        
        await update.message.reply_text(invite_text, parse_mode='Markdown')
    
    async def show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._show_balance(update, context)
    
    async def show_balance_farsi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._show_balance(update, context)
    
    async def _show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        username = update.message.from_user.first_name or "کاربر"
        user_coins = self.user_coins.get(user_id, 0)
        total_value = user_coins * 200
        current_time = datetime.now().strftime("%H:%M:%S")
        
        balance_text = (
            f"🥃 کاربر: {username}\n"
            f"🚜 موجودی: {user_coins} سکه\n"
            f"🫟 قیمت: {total_value:,} تومن\n"
            f"🍺 ساعت: {current_time}"
        )
        
        await update.message.reply_text(balance_text)
    
    async def transfer_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._transfer_coins(update, context)
    
    async def transfer_coins_farsi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._transfer_coins(update, context)
    
    async def _transfer_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        username = update.message.from_user.username or f"user_{user_id}"
        
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ لطفاً روی پیام کاربر مورد نظر ریپلای کنید و دستور را ارسال نمایید:\n"
                "مثال: `انتقال 10` یا `/transfer 10`"
            )
            return
        
        message_text = update.message.text
        coin_amount = 0
        
        try:
            if message_text.startswith('/transfer') and context.args:
                coin_amount = int(context.args[0])
            elif message_text.startswith('انتقال'):
                parts = message_text.split()
                if len(parts) >= 2:
                    coin_amount = int(parts[1])
            else:
                await update.message.reply_text(
                    "❌ فرمت دستور نادرست است!\n"
                    "مثال: `انتقال 10` یا `/transfer 10`"
                )
                return
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ لطفاً تعداد سکه را به درستی مشخص کنید:\n"
                "مثال: `انتقال 10` یا `/transfer 10`"
            )
            return
        
        if coin_amount <= 0:
            await update.message.reply_text("❌ تعداد سکه باید بیشتر از صفر باشد!")
            return
        
        if user_id not in self.user_coins or self.user_coins[user_id] < coin_amount:
            await update.message.reply_text(
                f"❌ موجودی سکه شما کافی نیست!\n"
                f"💰 موجودی فعلی: {self.user_coins.get(user_id, 0)} سکه\n"
                f"💸 سکه مورد نیاز: {coin_amount} سکه"
            )
            return
        
        target_user = update.message.reply_to_message.from_user
        target_user_id = target_user.id
        target_username = target_user.first_name or "کاربر"
        
        if target_user_id == user_id:
            await update.message.reply_text("❌ نمی‌توانید به خودتان سکه انتقال دهید!")
            return
        
        self.user_coins[user_id] -= coin_amount
        if target_user_id not in self.user_coins:
            self.user_coins[target_user_id] = 0
        self.user_coins[target_user_id] += coin_amount
        
        transfer_text = (
            f"💸 **انتقال سکه انجام شد**\n\n"
            f"👤 از: {username}\n"
            f"👥 به: {target_username}\n"
            f"💰 مبلغ: {coin_amount} سکه\n"
            f"💎 ارزش: {coin_amount * 200:,} تومن\n"
            f"🕐 زمان: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await update.message.reply_text(transfer_text)
        
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 شما {coin_amount} سکه از کاربر {username} دریافت کردید!\n"
                     f"💰 موجودی جدید: {self.user_coins[target_user_id]} سکه"
            )
        except:
            pass
    
    async def kasr_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if not self.is_owner(user_id):
            await update.message.reply_text("❌ شما دسترسی به این دستور را ندارید!")
            return
        
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ لطفاً روی پیام کاربر مورد نظر ریپلای کنید و دستور را ارسال نمایید:\n"
                "مثال: `/kasr 10`"
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ لطفاً تعداد سکه را مشخص کنید:\n"
                "مثال: `/kasr 10`"
            )
            return
        
        try:
            coin_amount = int(context.args[0])
            if coin_amount <= 0:
                await update.message.reply_text("❌ تعداد سکه باید بیشتر از صفر باشد!")
                return
            
            target_user = update.message.reply_to_message.from_user
            target_user_id = target_user.id
            target_username = target_user.first_name or "کاربر"
            
            current_coins = self.user_coins.get(target_user_id, 0)
            
            if current_coins < coin_amount:
                coins_to_deduct = current_coins
                self.user_coins[target_user_id] = 0
            else:
                coins_to_deduct = coin_amount
                self.user_coins[target_user_id] -= coin_amount
            
            kasr_text = (
                f"⚡ **کسر سکه توسط مالک**\n\n"
                f"👤 کاربر: {target_username}\n"
                f"🆔 آیدی: `{target_user_id}`\n"
                f"💰 مبلغ کسر شده: {coins_to_deduct} سکه\n"
                f"💎 موجودی جدید: {self.user_coins.get(target_user_id, 0)} سکه\n"
                f"🕐 زمان: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            await update.message.reply_text(kasr_text)
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"⚠️ {coins_to_deduct} سکه از حساب شما توسط مالک کسر شد!\n"
                         f"💰 موجودی جدید: {self.user_coins.get(target_user_id, 0)} سکه"
                )
            except:
                pass
                
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
    
    async def add_coins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if not self.is_owner(user_id):
            await update.message.reply_text("❌ شما دسترسی به این دستور را ندارید!")
            return
        
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ لطفاً روی پیام کاربر مورد نظر ریپلای کنید و دستور را ارسال نمایید:\n"
                "مثال: `/addcoins 10`"
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ لطفاً تعداد سکه را مشخص کنید:\n"
                "مثال: `/addcoins 10`"
            )
            return
        
        try:
            coin_amount = int(context.args[0])
            if coin_amount <= 0:
                await update.message.reply_text("❌ تعداد سکه باید بیشتر از صفر باشد!")
                return
            
            target_user = update.message.reply_to_message.from_user
            target_user_id = target_user.id
            target_username = target_user.first_name or "کاربر"
            
            if target_user_id not in self.user_coins:
                self.user_coins[target_user_id] = 0
            
            self.user_coins[target_user_id] += coin_amount
            
            add_text = (
                f"🎁 **افزودن سکه توسط مالک**\n\n"
                f"👤 کاربر: {target_username}\n"
                f"🆔 آیدی: `{target_user_id}`\n"
                f"💰 مبلغ افزوده شده: {coin_amount} سکه\n"
                f"💎 موجودی جدید: {self.user_coins.get(target_user_id, 0)} سکه\n"
                f"🕐 زمان: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            await update.message.reply_text(add_text)
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 {coin_amount} سکه توسط مالک به حساب شما افزوده شد!\n"
                         f"💰 موجودی جدید: {self.user_coins.get(target_user_id, 0)} سکه"
                )
            except:
                pass
                
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
    
    async def get_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if not self.is_owner(user_id):
            await update.message.reply_text("❌ شما دسترسی به این دستور را ندارید!")
            return
        
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ لطفاً روی پیام کاربر مورد نظر ریپلای کنید و دستور را ارسال نمایید:\n"
                "مثال: `/id`"
            )
            return
        
        target_user = update.message.reply_to_message.from_user
        target_user_id = target_user.id
        target_username = target_user.username or "ندارد"
        target_first_name = target_user.first_name or "ندارد"
        target_last_name = target_user.last_name or "ندارد"
        
        user_coins = self.user_coins.get(target_user_id, 0)
        total_value = user_coins * 200
        
        user_info_text = (
            f"👤 **اطلاعات کاربر**\n\n"
            f"🆔 **آیدی عددی:** `{target_user_id}`\n"
            f"👁️ **نام کاربری:** @{target_username}\n"
            f"📛 **نام:** {target_first_name}\n"
            f"📛 **نام خانوادگی:** {target_last_name}\n"
            f"💰 **تعداد سکه:** {user_coins}\n"
            f"💎 **ارزش سکه‌ها:** {total_value:,} تومن\n"
            f"🎯 **وضعیت سلف:** {'فعال' if target_user_id in self.active_selfbots else 'غیرفعال'}\n"
            f"📊 **تعداد دعوت‌ها:** {len(self.user_referrals.get(target_user_id, []))}\n"
            f"🕐 **زمان:** {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await update.message.reply_text(user_info_text, parse_mode='Markdown')
    
    def run(self):
        print("🤖 ربات SelfStruct System در حال اجراست...")
        print("👑 مالک ربات:", self.owner_id)
        print("💰 موجودی مالک: نامحدود")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# تنظیمات اصلی: مقادیر محرمانه فقط از Railway Variables خوانده می‌شوند.
if __name__ == "__main__":
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
    ADMIN_ID = os.environ.get("ADMIN_ID", "").strip()
    FORCE_CHANNEL = os.environ.get("FORCE_CHANNEL", "").strip()
    FORCE_CHANNEL_URL = os.environ.get("FORCE_CHANNEL_URL", "").strip()

    if not BOT_TOKEN:
        raise RuntimeError("متغیر BOT_TOKEN در Railway تنظیم نشده است.")
    if not ADMIN_ID.isdigit():
        raise RuntimeError("ADMIN_ID باید آیدی عددی ادمین باشد.")
    if not FORCE_CHANNEL or not FORCE_CHANNEL_URL.startswith("https://t.me/"):
        raise RuntimeError("FORCE_CHANNEL و FORCE_CHANNEL_URL را در Railway تنظیم کنید.")

    bot = TelegramAuthBot(BOT_TOKEN, int(ADMIN_ID), FORCE_CHANNEL, FORCE_CHANNEL_URL)
    bot.run()
