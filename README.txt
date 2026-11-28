NIRO project bundle
==================
Included: bot.py (main bot with betting/cards/wallet features), self.py (Pyrogram self-client source), helper.py (helper Telegram bot), assets, requirements.

Main bot (Railway):
- Set BOT_TOKEN and any needed ADMIN_IDS / OWNER_ID / payment/support settings in Railway Variables.
- Install requirements.txt and deploy. Procfile starts only the main bot.
- This package has not been runtime-tested against your live Telegram/Railway deployment.

Self client (owner-controlled local execution):
- Configure API_ID and API_HASH in your local .env file only.
- Run: python self.py
- Pyrogram asks for your own Telegram phone, login code and (if enabled) 2FA directly in the local terminal.
- Do NOT send codes, 2FA passwords or .session files to the bot, admin, or other users.
- Do not upload .env or session files to GitHub/Railway.
- The account automation source is not remotely provisioned by the main bot. Main bot UI provides informational panel only.

Helper bot:
- Set HELPER_TOKEN and HELPER_BOT_USERNAME in a private environment.
- Run separately: python helper.py
- The helper and self client communicate via local JSON files; do not run both on a shared remote host with other people's sessions.

Safety changes:
- Login-code interception/forwarding and storing Telegram login codes has been removed.
- No credentials are embedded in source.

Tested: Python syntax compilation only. Full live Telegram, betting, payment, and Railway tests remain required.
