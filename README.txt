NIRO SELF - Python Telegram Bot

Local / Termux:
1) Install Python 3 and run: pip install -r requirements.txt
2) Set environment variables from .env.example (do not upload real token to GitHub).
3) Run: python bot.py

Railway:
1) Upload these files to a GitHub repository.
2) Create a Railway Worker service from the repository.
3) Add the variables from .env.example in Railway Variables.
4) Start command: python bot.py (or use the included Procfile).
5) Use a persistent volume and set DB_PATH to a path on that volume, e.g. /data/niro_self.sqlite3.

Important:
- Add the bot to your group and promote it to admin for group functions.
- Configure BET_GROUP_LINK with the actual group invite URL.
- Set OWNER_ID, ADMIN_IDS, CARD_NUMBER, CARD_OWNER, SUPPORT_USERNAME.
- This version implements the diamond ledger, receipt approval, referral rewards, group dice game, balance and reply-transfer.
- Selfbot activation/deactivation is only a placeholder: the actual user-account session manager is not connected yet.
- The bot cannot make a user a group admin; do that manually in Telegram.
