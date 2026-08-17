<?php
/* ########################## @Pv_MrMahdi ######################### */
/*
╭─────────────────────────────────────────────────────────────╮
                            ⚡ DARK TEAM ⚡

                          ✦ ذکر منبع الزامی است

                       👨‍💻 نویسنده : @Pv_MrMahdi

                     🔓 اوپن کننده : @Sourrce_kade

╰─────────────────────────────────────────────────────────────╯
*/
/* ####################### @Pv_MrMahdi ############################ */
// bot.php
error_reporting(0);
require_once 'config.php';
require_once 'ads.php';

// دریافت آپدیت‌ها از تلگرام
$update = json_decode(file_get_contents('php://input'));

function bot($method, $datas = []) {
    $url = "https://api.telegram.org/bot" . BOT_TOKEN . "/" . $method;
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $datas);
    $res = curl_exec($ch);
    return json_decode($res, true);
}

if (!$update) exit;

$db = getDB();

// استخراج اطلاعات پیام 
if (isset($update->message)) {
    $chat_id = $update->message->chat->id;
    $from_id = $update->message->from->id;
    $text = $update->message->text;
    $username = isset($update->message->from->username) ? "@" . $update->message->from->username : "ندارد";
    $first_name = $update->message->from->first_name;
    $message_id = $update->message->message_id;
    $is_callback = false;
} elseif (isset($update->callback_query)) {
    $chat_id = $update->callback_query->message->chat->id;
    $from_id = $update->callback_query->from->id;
    $data = $update->callback_query->data;
    $username = isset($update->callback_query->from->username) ? "@" . $update->callback_query->from->username : "ندارد";
    $first_name = $update->callback_query->from->first_name;
    $message_id = $update->callback_query->message->message_id;
    $is_callback = true;
}

// ثبت‌نام کاربر جدید
if (isset($update->message) && !isset($db['users'][$from_id])) {
    $db['users'][$from_id] = [
        'name' => $first_name,
        'username' => $username,
        'id' => $from_id,
        'date' => date('Y-m-d H:i'),
        'banned' => false
    ];
    saveDB($db);
}


if ($db['status'] == 'off' && $from_id != OWNER_ID && !in_array($from_id, $db['admins'])) {
    if (!$is_callback) {
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ ربات موقتاً خاموش و در دست تعمیر است."]);
    }
    exit;
}

// بررسی بن بودن کاربر
if (isset($db['users'][$from_id]['banned']) && $db['users'][$from_id]['banned'] == true) {
    if (!$is_callback) {
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ شما از دسترسی به این ربات محروم (بلاک) شده‌اید."]);
    }
    exit;
}

if (
    !$is_callback &&
    $from_id != OWNER_ID &&
    !in_array($from_id, $db['admins']) &&
    !empty($db['channels'])
) {
    $not_joined = [];

    foreach ($db['channels'] as $channel) {
        $channel = ltrim(trim($channel), "@");
        $check = bot('getChatMember', [
            'chat_id' => "@".$channel,
            'user_id' => $from_id
        ]);
        $status = $check['result']['status'] ?? '';
        if (!in_array($status, ['member','administrator','creator'])) {
            $not_joined[] = $channel;
        }
    }

    if (!empty($not_joined)) {
        $buttons = [];
        foreach ($not_joined as $channel) {
            $buttons[] = [[
                'text' => "📢 @$channel",
                'url' => "https://t.me/$channel"
            ]];
        }
        $buttons[] = [[
            'text' => "✅ عضو شدم",
            'callback_data' => "check_join"
        ]];

        bot('sendMessage',[
            'chat_id'=>$chat_id,
            'text'=>"⚠️ ابتدا در کانال‌های زیر عضو شوید و سپس روی «✅ عضو شدم» بزنید.",
            'reply_markup'=>json_encode([
                'inline_keyboard'=>$buttons
            ])
        ]);
        exit;
    }
}

$main_menu = json_encode([
    'inline_keyboard' => [
        [['text' => 'Webhook ✅', 'callback_data' => 'menu_webhook']],
       
        [
            ['text' => '🔥 اسپانسر', 'callback_data' => 'menu_sponsor'], 
            ['text' => 'تبلیغات 💬', 'callback_data' => 'menu_ads']
        ],
        [['text' => 'پشتیبانی 🤖', 'callback_data' => 'menu_support']],
        [['text' => 'پنل مدیریت 🚀', 'callback_data' => 'menu_admin']]
    ]
]);

// بازگشت به منوی اصلی
if ($is_callback && $data == 'back_main') {
    $db['steps'][$from_id] = null; saveDB($db);
    bot('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $message_id,
        'text' => "👋 به منوی اصلی خوش آمدید. گزینه مورد نظر خود را انتخاب کنید:",
        'reply_markup' => $main_menu
    ]);
    exit;
}

/* ####################### @Pv_MrMahdi ############################ */

if ($is_callback && $data == "check_join") {
    $not_joined = [];

    foreach ($db['channels'] as $channel) {
        $channel = ltrim(trim($channel), "@");
        $check = bot('getChatMember', [
            'chat_id' => "@".$channel,
            'user_id' => $from_id
        ]);
        $status = $check['result']['status'] ?? '';
        if (!in_array($status, ['member','administrator','creator'])) {
            $not_joined[] = $channel;
        }
    }

    if (!empty($not_joined)) {
        bot('answerCallbackQuery',[
            'callback_query_id'=>$update->callback_query->id,
            'text'=>"❌ هنوز در همه کانال‌ها عضو نشده‌اید.",
            'show_alert'=>true
        ]);
    } else {
        bot('answerCallbackQuery',[
            'callback_query_id'=>$update->callback_query->id,
            'text'=>"✅ عضویت تایید شد."
        ]);
        bot('deleteMessage',[
            'chat_id'=>$chat_id,
            'message_id'=>$message_id
        ]);
        
 
        bot('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "👋 به منوی اصلی خوش آمدید. گزینه مورد نظر خود را انتخاب کنید:",
            'reply_markup' => $main_menu
        ]);
    }
    exit;
}/* ###################### @Pv_MrMahdi ############################ */
if (!$is_callback && $text == '/start') {
    $db['steps'][$from_id] = null; saveDB($db);
    bot('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "👋 سلام! به ربات ست‌وبهوک پیشرفته خوش آمدید.\nلطفاً از دکمه‌های شیشه‌ای زیر استفاده کنید:",
        'reply_markup' => $main_menu
    ]);
    exit;
}


if ($is_callback && $data == 'menu_webhook') {
    $db['steps'][$from_id] = 'wait_token'; saveDB($db);
    bot('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $message_id,
        'text' => "🔑 لطفاً توکن ربات خود را ارسال کنید:",
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منو', 'callback_data' => 'back_main']]]])
    ]);
    exit;
}

if (!$is_callback && ($db['steps'][$from_id] ?? '') == 'wait_token_info') {
    
    // ۱. گرفتن اطلاعات ربات با متد getMe
    $ch_test = curl_init("https://api.telegram.org/bot" . $text . "/getMe");
    curl_setopt($ch_test, CURLOPT_RETURNTRANSFER, true);
    $res_test = json_decode(curl_exec($ch_test), true);
    
    // ۲. گرفتن اطلاعات وب‌هوک با متد getWebhookInfo
    $ch_wh = curl_init("https://api.telegram.org/bot" . $text . "/getWebhookInfo");
    curl_setopt($ch_wh, CURLOPT_RETURNTRANSFER, true);
    $res_wh = json_decode(curl_exec($ch_wh), true);
    
    // ۳. بررسی اعتبار توکن
    if ($res_test['ok'] == true) {
        $bot_name = $res_test['result']['first_name'];
        $bot_user = "@" . $res_test['result']['username'];
        $webhook_url = $res_wh['result']['url'] ?: "ست نشده ❌";
        
        // پاک کردن وضعیت کاربر از دیتابیس
        $db['steps'][$from_id] = null; 
        saveDB($db);
        
        
        bot('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ اطلاعات توکن دریافتی:\n\n👤 نام ربات: $bot_name\n🆔 آیدی ربات: $bot_user\n\n🌐 آدرس ست شده:\n`$webhook_url`",
            'parse_mode' => 'Markdown',
            'reply_markup' => $main_menu
        ]);
    } else {
        
        bot('sendMessage', [
            'chat_id' => $chat_id, 
            'text' => "❌ توکن نامعتبر است! لطفاً توکن صحیح را ارسال کنید:",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منو', 'callback_data' => 'back_main']]]])
        ]);
    }
    exit;
}

// پردازش توکن ارسالی
if (!$is_callback && ($db['steps'][$from_id] ?? '') == 'wait_token') {
    bot('deleteMessage', ['chat_id' => $chat_id, 'message_id' => $message_id - 1]);
    bot('deleteMessage', ['chat_id' => $chat_id, 'message_id' => $message_id]);
    
    $ch_test = curl_init("https://api.telegram.org/bot" . $text . "/getMe");
    curl_setopt($ch_test, CURLOPT_RETURNTRANSFER, true);
    $res_test = json_decode(curl_exec($ch_test), true);
    
    if ($res_test['ok'] == true) {
        $bot_name = $res_test['result']['first_name'];
        $bot_user = "@" . $res_test['result']['username'];
        
        $db['steps'][$from_id] = 'wait_url|' . $text . '|' . $bot_name . '|' . $bot_user;
        saveDB($db);
        
        bot('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ توکن شما دریافت شد.\n\n👤 نام ربات: $bot_name\n🆔 آیدی ربات: $bot_user\n\n🌐 حالا آدرس دقیق فایل خود (مثلاً شامل bot.php یا py.php) را بفرستید:",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منو', 'callback_data' => 'back_main']]]])
        ]);
    } else {
        bot('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ توکن ارسال شده نامعتبر است! لطفاً مجدداً توکن درست را ارسال کنید:",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منو', 'callback_data' => 'back_main']]]])
        ]);
    }
    exit;
}


if (!$is_callback && explode('|', $db['steps'][$from_id] ?? '')[0] == 'wait_url') {
    $parts = explode('|', $db['steps'][$from_id]);
    $user_token = $parts[1];
    $bot_name = $parts[2];
    $bot_user = $parts[3];
    $user_url = $text;
    
    bot('deleteMessage', ['chat_id' => $chat_id, 'message_id' => $message_id - 1]);
    bot('deleteMessage', ['chat_id' => $chat_id, 'message_id' => $message_id]);
    
    if (filter_var($user_url, FILTER_VALIDATE_URL)) {
        $ch_set = curl_init("https://api.telegram.org/bot" . $user_token . "/setWebhook?url=" . urlencode($user_url));
        curl_setopt($ch_set, CURLOPT_RETURNTRANSFER, true);
        $res_set = json_decode(curl_exec($ch_set), true);
        
        if ($res_set['ok'] == true) {
            $db['steps'][$from_id] = null;
            $db['webhooks'][] = [
                'user_id' => $from_id,
                'username' => $username,
                'token' => $user_token,
                'url' => $user_url,
                'bot_username' => $bot_user
            ];
            saveDB($db);
            
            bot('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "🚀 ربات شما با موفقیت تنظیم وبهوک (ست وبهوک) شد.\n\n🆔 آیدی ربات: $bot_user\n🌐 آدرس ست شده:\n`$user_url`",
                'parse_mode' => 'Markdown'
            ]);
            
            bot('sendMessage', [
                'chat_id' => IdAddy, // ایدی عددی ادمین
                'text' => "🔔 ربات جدیدی تنظیم وبهوک شد!\n\n📋 مشخصات ربات:\nنام ربات: $bot_name\nیوزرنیم ربات: $bot_user\n\n🌐 آدرس ست شده:\n`$user_url`\n\n👤 آیدی ست کننده: $username\n🔢 آیدی عددی ست کننده: $from_id",
                'parse_mode' => 'Markdown'
            ]);
        } else {
            bot('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "❌ ارتباط با آدرس مقدور نیست. لطفاً آدرس معتبر تری بفرستید:",
                'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منو', 'callback_data' => 'back_main']]]])
            ]);
        }
    } else {
        bot('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ آدرس ارسال شده نامعتبر است! مجدداً ارسال کنید:",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منو', 'callback_data' => 'back_main']]]])
        ]);
    }
    exit;
}


if ($is_callback && $data == 'menu_sponsor') {
    bot('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $message_id,
        'text' => SPONSOR_TEXT,
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => 'ورود به کانال اسپانسر 🚀', 'url' => SPONSOR_URL]],
                [['text' => '🔙 بازگشت', 'callback_data' => 'back_main']]
            ]
        ])
    ]);
    exit;
}


if ($is_callback && $data == 'menu_ads') {
    bot('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $message_id,
        'text' => $ads_text,
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => '📣 ثبت تبلیغ جدید', 'url' => $ads_link]],
                [['text' => '🔙 بازگشت', 'callback_data' => 'back_main']]
            ]
        ])
    ]);
    exit;
}


if ($is_callback && $data == 'menu_support') {
    $db['steps'][$from_id] = 'wait_support'; saveDB($db);
    bot('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $message_id,
        'text' => "📥 لطفاً پیام خود را بفرستید تا به پشتیبانی ارسال شود:",
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف و بازگشت', 'callback_data' => 'back_main']]]])
    ]);
    exit;
}

if (!$is_callback && ($db['steps'][$from_id] ?? '') == 'wait_support') {
    $db['steps'][$from_id] = null; saveDB($db);
    
    bot('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ پیام شما با موفقیت به پشتیبانی ارسال شد."]);
    bot('forwardMessage', ['chat_id' => OWNER_ID, 'from_chat_id' => $chat_id, 'message_id' => $message_id]);
    
    $user_webhooks_count = 0; $user_urls = ""; $user_bots = "";
    foreach ($db['webhooks'] as $w) {
        if ($w['user_id'] == $from_id) {
            $user_webhooks_count++;
            $user_urls .= $user_webhooks_count . "- " . $w['url'] . "\n";
            $user_bots .= $user_webhooks_count . "- " . $w['bot_username'] . "\n";
        }
    }
    if ($user_urls == "") $user_urls = "هیچ\n";
    if ($user_bots == "") $user_bots = "هیچ\n";
    
    bot('sendMessage', [
        'chat_id' => OWNER_ID,
        'text' => "👤 مشخصات فرستنده پیام پشتیبانی:\n\nنام کاربر: $first_name\nیوزرنیم: $username\nآیدی عددی: `$from_id\n`🔢 تعداد ست وبهوک: $user_webhooks_count\n\n🌐 آدرس‌های ست شده:\n$user_urls\n🤖 آیدی ربات‌های ست شده:\n$user_bots"
    ]);
    exit;
}

/* ####################### @Pv_MrMahdi ############################ */

if ($is_callback && $data == 'menu_admin') {
    if ($from_id != OWNER_ID && !in_array($from_id, $db['admins'])) {
        bot('answerCallbackQuery', ['callback_query_id' => $update->callback_query->id, 'text' => '❌ شما ادمین نیستید.', 'show_alert' => true]);
        exit;
    }
    
    $admin_menu = [
        'inline_keyboard' => [
            [['text' => '📊 آمار ربات', 'callback_data' => 'adm_stats']],
            [
                ['text' => '➕ افزودن کانال', 'callback_data' => 'adm_add_ch'], 
                ['text' => '❌ حذف کانال', 'callback_data' => 'adm_rem_ch']
            ],
            [
                ['text' => '➕ افزودن ادمین', 'callback_data' => 'adm_add_adm'], 
                ['text' => '❌ حذف ادمین', 'callback_data' => 'adm_rem_adm']
            ],
            [
                ['text' => '🚫 مسدود (بن)', 'callback_data' => 'adm_ban'], 
                ['text' => '🟢 رفع مسدود (آنبن)', 'callback_data' => 'adm_unban']
            ],
            [
                ['text' => '📋 لیست کانال‌ها', 'callback_data' => 'adm_list_ch'], 
                ['text' => '📋 لیست ادمین‌ها', 'callback_data' => 'adm_list_adm']
            ],
            [
                ['text' => '🔴 خاموش کردن', 'callback_data' => 'adm_off'], 
                ['text' => '🟢 روشن کردن', 'callback_data' => 'adm_on']
            ],
            [
                ['text' => '📝 ارسال همگانی', 'callback_data' => 'adm_send_all'], 
                ['text' => '🔄 فوروارد همگانی', 'callback_data' => 'adm_fwd_all']
            ],
            [['text' => '👤 ارسال به یک کاربر', 'callback_data' => 'adm_send_user']],
            [
                ['text' => '📂 فایل ممبر', 'callback_data' => 'adm_file_users'], 
                ['text' => '📂 فایل توکن‌ها', 'callback_data' => 'adm_file_tokens']
            ],
            [['text' => '🔙 بازگشت به منوی اصلی', 'callback_data' => 'back_main']]
        ]
    ];
    
    bot('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $message_id,
        'text' => "🚀 به پنل ادمین خوش آمدید. دستور مدیریتی را انتخاب کنید:",
        'reply_markup' => json_encode($admin_menu)
    ]);
    exit;
}

if ($is_callback && $data == 'back_admin_panel') {
    $db['steps'][$from_id] = null; saveDB($db);
    $admin_menu = [
        'inline_keyboard' => [
            [['text' => '📊 آمار ربات', 'callback_data' => 'adm_stats']],
            [['text' => '➕ افزودن کانال', 'callback_data' => 'adm_add_ch'], ['text' => '❌ حذف کانال', 'callback_data' => 'adm_rem_ch']],
            [['text' => '➕ افزودن ادمین', 'callback_data' => 'adm_add_adm'], ['text' => '❌ حذف ادمین', 'callback_data' => 'adm_rem_adm']],
            [['text' => '🚫 مسدود (بن)', 'callback_data' => 'adm_ban'], ['text' => '🟢 رفع مسدود (آنبن)', 'callback_data' => 'adm_unban']],
            [['text' => '📋 لیست کانال‌ها', 'callback_data' => 'adm_list_ch'], ['text' => '📋 لیست ادمین‌ها', 'callback_data' => 'adm_list_adm']],
            [['text' => '🔴 خاموش کردن', 'callback_data' => 'adm_off'], ['text' => '🟢 روشن کردن', 'callback_data' => 'adm_on']],
            [['text' => '📝 ارسال همگانی', 'callback_data' => 'adm_send_all'], ['text' => '🔄 فوروارد همگانی', 'callback_data' => 'adm_fwd_all']],
            [['text' => '👤 ارسال به یک کاربر', 'callback_data' => 'adm_send_user']],
            [['text' => '📂 فایل ممبر', 'callback_data' => 'adm_file_users'], ['text' => '📂 فایل توکن‌ها', 'callback_data' => 'adm_file_tokens']],
            [['text' => '🔙 بازگشت به منوی اصلی', 'callback_data' => 'back_main']]
        ]
    ];
    bot('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $message_id,
        'text' => "🚀 به پنل مدیریت برگشتید:",
        'reply_markup' => json_encode($admin_menu)
    ]);
    exit;
}

/* ####################### @Pv_MrMahdi ############################ */


if ($is_callback) {
    if ($data == 'adm_stats') {
        $total_users = count($db['users']); $total_wh = count($db['webhooks']);
        $active_users = 0; $inactive_users = 0;
        foreach($db['users'] as $u) {
            if(isset($u['banned']) && $u['banned'] == true) $inactive_users++; else $active_users++;
        }
        bot('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $message_id,
            'text' => "📊 آمار کاربران ربات:\n\n🟢 تعداد کاربر فعال: $active_users\n🔴 تعداد کاربر غیرفعال (مسدود): $inactive_users\n👥 کل کاربران: $total_users\n\n🔄 تعداد ست وبهوک‌های انجام شده: $total_wh",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'back_admin_panel']]]])
        ]);
        exit;
    }
    
    if ($data == 'adm_off') {
        $db['status'] = 'off'; saveDB($db);
        bot('answerCallbackQuery', ['callback_query_id' => $update->callback_query->id, 'text' => '🔴 ربات با موفقیت خاموش شد.', 'show_alert' => true]);
        exit;
    }
    if ($data == 'adm_on') {
        $db['status'] = 'on'; saveDB($db);
        bot('answerCallbackQuery', ['callback_query_id' => $update->callback_query->id, 'text' => '🟢 ربات با موفقیت روشن شد.', 'show_alert' => true]);
        exit;
    }
    
    if ($data == 'adm_list_ch') {
        $txt = "🔵 لیست کانال‌های جوین اجباری:\n\n";
        foreach($db['channels'] as $ch) $txt .= "📣 @$ch\n";
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => $txt, 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'back_admin_panel']]]])]);
        exit;
    }
    if ($data == 'adm_list_adm') {
        $txt = "🟢 لیست ادمین‌های ربات:\n\n";
        foreach($db['admins'] as $adm) $txt .= "👤 `$adm`\n";
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => $txt, 'parse_mode' => 'Markdown', 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'back_admin_panel']]]])]);
        exit;
    }

    $sensitive_actions = ['adm_add_adm', 'adm_rem_adm', 'adm_add_ch', 'adm_rem_ch', 'adm_file_users', 'adm_file_tokens', 'adm_ban', 'adm_unban'];
    if (in_array($data, $sensitive_actions) && $from_id != OWNER_ID) {
        bot('answerCallbackQuery', ['callback_query_id' => $update->callback_query->id, 'text' => '❌ خطای امنیتی: این بخش منحصراً در دسترس مالک اصلی ربات است.', 'show_alert' => true]);
        exit;
    }

    if ($data == 'adm_add_adm') {
        $db['steps'][$from_id] = 'add_admin_step'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => "🔢 لطفاً آیدی عددی ادمین جدید را بفرستید:", 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    if ($data == 'adm_rem_adm') {
        $txt = "❌ لیست ادمین‌ها جهت حذف:\n\n";
        foreach($db['admins'] as $adm) $txt .= "👤 `$adm`\n";
        $txt .= "\nکدام ادمین را می‌خواهید حذف کنید؟ آیدی عددی او را بفرستید:";
        $db['steps'][$from_id] = 'rem_admin_step'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => $txt, 'parse_mode' => 'Markdown', 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    if ($data == 'adm_add_ch') {
        $db['steps'][$from_id] = 'add_chan_step'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => "📣 آیدی کانال را بدون علامت @ بفرستید:", 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    if ($data == 'adm_rem_ch') {
        $db['steps'][$from_id] = 'rem_chan_step'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => "❌ آیدی کانال مورد نظر جهت حذف را بدون @ بفرستید:", 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    if ($data == 'adm_ban') {
        $db['steps'][$from_id] = 'ban_user_step'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => "🚫 آیدی عددی کاربر مورد نظر جهت بن را بفرستید:", 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    if ($data == 'adm_unban') {
        $db['steps'][$from_id] = 'unban_user_step'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => "🟢 آیدی عددی کاربر مورد نظر جهت رفع بن را بفرستید:", 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    if ($data == 'adm_send_all') {
        $db['steps'][$from_id] = 'send_all_step'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => "📝 متن پیام همگانی خود را بفرستید:", 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    if ($data == 'adm_fwd_all') {
        $db['steps'][$from_id] = 'fwd_all_step'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => "🔄 پیام مورد نظر خود را اینجا فوروارد کنید:", 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    if ($data == 'adm_send_user') {
        $db['steps'][$from_id] = 'send_user_step1'; saveDB($db);
        bot('editMessageText', ['chat_id' => $chat_id, 'message_id' => $message_id, 'text' => "🔢 آیدی عددی کاربر هدف را ارسال کنید:", 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'back_admin_panel']]]])]); exit;
    }
    
    if ($data == 'adm_file_users') {
        $content = "";
        foreach($db['users'] as $u) {
            $u_id = $u['id']; $wh_list = "";
            foreach($db['webhooks'] as $w) { if($w['user_id'] == $u_id) $wh_list .= $w['url'] . " | "; }
            if($wh_list == "") $wh_list = "بدون آدرس ست شده";
            $content .= "نام : " . $u['name'] . "\nیوزرنیم : " . $u['username'] . "\nآیدی عددی : " . $u_id . "\nتاریخ عضویت : " . $u['date'] . "\nآدرس‌های ست شده :\n" . $wh_list . "\n---------------------\nکاربر بعدی\n\n";
        }
        file_put_contents('members.txt', $content);
        bot('sendDocument', ['chat_id' => $chat_id, 'document' => new CURLFile('members.txt'), 'caption' => '📂 لیست کامل ممبرها']);
        unlink('members.txt'); exit;
    }
    
    if ($data == 'adm_file_tokens') {
        $content = ""; $grouped = [];
        foreach($db['webhooks'] as $w) { $grouped[$w['user_id']][] = "توکن: " . $w['token'] . " | آدرس فایل: " . $w['url']; }
        foreach($db['users'] as $u) {
            $u_id = $u['id'];
            if(isset($grouped[$u_id])) {
                $content .= "نام کاربر : " . $u['name'] . "\nیوزرنیم : " . $u['username'] . "\nتوکن‌های ست شده همراه با آدرس فایل :\n";
                foreach($grouped[$u_id] as $i => $line) { $content .= ($i+1) . " " . $line . "\n"; }
                $content .= "---------------------\nو بعدی\n\n";
            }
        }
        file_put_contents('tokens.txt', $content);
        bot('sendDocument', ['chat_id' => $chat_id, 'document' => new CURLFile('tokens.txt'), 'caption' => '📂 لیست کامل توکن‌ها']);
        unlink('tokens.txt'); exit;
    }
}

/* ####################### @Pv_MrMahdi ############################ */

if (!$is_callback && !empty($db['steps'][$from_id])) {
    $step = $db['steps'][$from_id];
    
    if ($step == 'add_admin_step') {
        $db['admins'][] = (int)$text; $db['steps'][$from_id] = null; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ کاربر $text با موفقیت ادمین شد.", 'reply_markup' => $main_menu]); exit;
    }
    if ($step == 'rem_admin_step') {
        if ($text == OWNER_ID) { bot('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ شما نمی‌توانید مالک اصلی را حذف کنید!"]); exit; }
        $db['admins'] = array_diff($db['admins'], [(int)$text]); $db['steps'][$from_id] = null; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ ادمین با آیدی $text حذف شد.", 'reply_markup' => $main_menu]); exit;
    }
    if ($step == 'add_chan_step') {
        $clean_ch = str_replace('@', '', $text);
        $db['channels'][] = $clean_ch; $db['steps'][$from_id] = null; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "📣 کانال @$clean_ch به لیست جوین اجباری افزوده شد.", 'reply_markup' => $main_menu]); exit;
    }
    if ($step == 'rem_chan_step') {
        $clean_ch = str_replace('@', '', $text);
        $db['channels'] = array_diff($db['channels'], [$clean_ch]); $db['steps'][$from_id] = null; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ کانال @$clean_ch از لیست جوین اجباری حذف شد.", 'reply_markup' => $main_menu]); exit;
    }
    if ($step == 'ban_user_step') {
        if ($text == OWNER_ID) { bot('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ امکان مسدودسازی مالک اصلی وجود ندارد."]); exit; }
        $db['users'][(int)$text]['banned'] = true; $db['steps'][$from_id] = null; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "🚫 کاربر $text مسدود شد.", 'reply_markup' => $main_menu]); exit;
    }
    if ($step == 'unban_user_step') {
        $db['users'][(int)$text]['banned'] = false; $db['steps'][$from_id] = null; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "🟢 کاربر $text رفع مسدودیت شد.", 'reply_markup' => $main_menu]); exit;
    }
    if ($step == 'send_all_step') {
        $db['steps'][$from_id] = null; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "🔄 ارسال پیام همگانی آغاز شد..."]);
        foreach($db['users'] as $u) { bot('sendMessage', ['chat_id' => $u['id'], 'text' => $text]); }
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ پیام همگانی با موفقیت ارسال شد."]); exit;
    }
    if ($step == 'fwd_all_step') {
        $db['steps'][$from_id] = null; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "🔄 فوروارد همگانی آغاز شد..."]);
        foreach($db['users'] as $u) { bot('forwardMessage', ['chat_id' => $u['id'], 'from_chat_id' => $chat_id, 'message_id' => $message_id]); }
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ فوروارد همگانی با موفقیت انجام شد."]); exit;
    }
    if ($step == 'send_user_step1') {
        $db['steps'][$from_id] = 'send_user_step2|' . $text; saveDB($db);
        bot('sendMessage', ['chat_id' => $chat_id, 'text' => "📝 حالا متن پیام خود را برای کاربر بفرستید:"]); exit;
    }
    if (explode('|', $step)[0] == 'send_user_step2') {
        $target = explode('|', $step)[1]; $db['steps'][$from_id] = null; saveDB($db);
        $res = bot('sendMessage', ['chat_id' => $target, 'text' => $text]);
        if($res['ok'] == true) {
            bot('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ پیام شما با موفقیت به کاربر $target تحویل داده شد."]);
        } else {
            bot('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ ارسال پیام ناموفق بود."]);
        }
        exit;
    }
}
/*
╭─────────────────────────────────────────────────────────────╮
                            ⚡ DARK TEAM ⚡

                          ✦ ذکر منبع الزامی است

                       👨‍💻 نویسنده : @Pv_MrMahdi

                     🔓 اوپن کننده : @Sourrce_kade

╰─────────────────────────────────────────────────────────────╯
*/
?>