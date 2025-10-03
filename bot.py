from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import os
import tempfile
import pandas as pd

TOKEN = os.getenv("BOT_TOKEN")

def check_username(uname: str) -> str:
    tg_url = f"https://t.me/{uname}"
    try:
        r = requests.get(tg_url, allow_redirects=True, timeout=5)
        html = r.text.lower()
    except Exception as e:
        return f"⚠️ Fehler: {e}"

    # Debug hilft: printen für Heroku Logs
    print(f"Check {uname}: status={r.status_code}, snippet={html[:150]}")

    if r.status_code == 404 or "username not occupied" in html:
        return "✅ Frei"
    if "if you have telegram" in html:
        return "❌ Vergeben"
    if "this username is not available" in html or "invalid invite link" in html:
        return "🚫 Banned"

    return "❌ Vergeben"

def check_text(update, context):
    usernames = [u.strip("@").lower() for u in update.message.text.split() if len(u) >= 4]
    free_names = [f"@{u}" for u in usernames if check_username(u) == "✅ Frei"]

    if free_names:
        update.message.reply_text("✅ Frei:\n" + " ".join(free_names))
    else:
        update.message.reply_text("Keine wirklich freien Usernames gefunden.")

def check_file(update, context):
    file = update.message.document.get_file()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        file.download(custom_path=tmp.name)
        with open(tmp.name, "r", encoding="utf-8") as f:
            usernames = [line.strip().lower().replace("@", "") for line in f if line.strip()]

    free_data = [{"username": u, "status": "✅ Frei"} for u in usernames if check_username(u) == "✅ Frei"]

    if not free_data:
        update.message.reply_text("Keine wirklich freien Usernames in der Datei gefunden.")
        return

    df = pd.DataFrame(free_data)
    out_path = tempfile.mktemp(suffix=".csv")
    df.to_csv(out_path, index=False, encoding="utf-8")

    free_names = [f"@{d['username']}" for d in free_data]
    update.message.reply_text("✅ Frei:\n" + " ".join(free_names))
    with open(out_path, "rb") as f:
        update.message.reply_document(f, filename="free_usernames.csv", caption="Liste aller freien Usernames")

def debug(update, context):
    if not context.args:
        update.message.reply_text("Benutze: /debug <username>")
        return
    uname = context.args[0].strip("@").lower()
    tg_url = f"https://t.me/{uname}"
    r = requests.get(tg_url, allow_redirects=True, timeout=5)
    update.message.reply_text(f"Status: {r.status_code}\nSnippet: {r.text[:300]}")

def start(update, context):
    update.message.reply_text("Schick mir Usernames (Text oder .txt-Datei).\nNutze /debug <username> für Rohdaten.")

if __name__ == "__main__":
    print("🚀 Bot startet...")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("debug", debug))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, check_text))
    dp.add_handler(MessageHandler(Filters.document.mime_type("text/plain"), check_file))

    updater.start_polling()
    print("✅ Bot läuft (Polling aktiv)")
    updater.idle()
