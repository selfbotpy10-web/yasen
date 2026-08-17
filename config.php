<?php
// config.php


define('BOT_TOKEN', 'BotToken'); // توکن ربات 


define('OWNER_ID', IdAddy); // آیدی عددی ادمین اصلی


define('DB_FILE', 'database.json'); // نام فایل ذخیره کاربران

// دکمه اسپانسر
define('SPONSOR_TEXT', '🔥 به بزرگترین مرجع سورس‌های رایگان بپیوندید!');
define('SPONSOR_URL', 'https://t.me/Sourrce_kade');

// توابع کمکی برای دیتابیس 
function getDB() {
    if (!file_exists(DB_FILE)) {
        $initial = [
            'users' => [],
            'admins' => [OWNER_ID],
            'channels' => [],
            'webhooks' => [],
            'status' => 'on',
            'steps' => []
        ];
        file_put_contents(DB_FILE, json_encode($initial, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    }
    return json_decode(file_get_contents(DB_FILE), true);
}

function saveDB($data) {
    file_put_contents(DB_FILE, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
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
