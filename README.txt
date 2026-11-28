NIRO VIP wallet and wager cards - complete replacement files

Upload these files together to the same GitHub branch/root folder used by Railway:
- bot.py (replace the existing bot.py)
- wallet_template.png
- DejaVuSans.ttf
- DejaVuSans-Bold.ttf
- requirements.txt

Railway start command remains:
python -u bot.py

This version renders the wallet card and bet card using bundled fonts. Wallet card uses the user's live balance/profile. Bet card uses both players' profile photos/IDs when the opponent joins; shows stake, net prize and calculated tax.

Note: preserve your existing Railway environment variables and database file/storage configuration. Syntax compilation was checked, but the Telegram bot was not live-tested in this environment.
