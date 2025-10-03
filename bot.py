from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import os
import tempfile
import pandas as pd

# Bot-Token aus Heroku Config Vars
TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def check_username(uname: str) -> str:
    """Prüft, ob Username frei, vergeben oder banned ist (Telegram API)"""
    url = f"{API_URL}/getChat?username={uname}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
    except Exception as e:
        return f"⚠️ Fehler: {e}"

    # Wenn Chat existiert -> vergeben
    if data.get("ok") is True:
        return "❌ Vergeben"

    # Fehlerbeschreibung prüfen
    desc = data.get("description", "").lower()

    if "not occupied" in desc or "chat not found" in desc:
        return "✅ Frei"     # wirklich claimbar
    if "invalid" in desc:
        return "🚫 Banned"
    if "occupied" in desc:
        return "❌ Vergeben"

    return f"⚠️ Unbekannt ({desc})"

def check_text(update, context):
    """Check von Usernames direkt aus Text"""
    usernames = [u.strip("@").lower() for u in update.message.text.split() if len(u) >= 4]
    free_names = [f"@{u}" for u in usernames if check_username(u) == "✅ Frei"]

    if free_names:
        update.message.reply_text("✅ Frei:\n" + " ".join(free_names))
    else:
        update.message.reply_text("Keine wirklich freien Usernames gefunden.")

def check_file(update, context):
    """Check von Usernames aus hochgeladener TXT-Datei"""
    file = update.message.document.get_file()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        file.download(custom_path=tmp.name)
        with open(tmp.name, "r", encoding="utf-8") as f:
            usernames = [line.strip().lower().replace("@", "") for line in f if line.strip()]

    free_data = [{"username": u, "status": "✅ Frei"} for u in usernames if check_username(u) == "✅ Frei"]

    if not free_data:
        update.message.reply_text("Keine wirklich freien Usernames in der Datei gefunden.")
        return

    # CSV mit freien Namen speichern
    df = pd.DataFrame(free_data)
    out_path = tempfile.mktemp(suffix=".csv")
    df.to_csv(out_path, index=False, encoding="utf-8")

    # Ergebnisse schicken
    free_names = [f"@{d['username']}" for d in free_data]
    update.message.reply_text("✅ Frei:\n" + " ".join(free_names))
    with open(out_path, "rb") as f:
        update.message.reply_document(f, filename="free_usernames.csv", caption="Liste aller freien Usernames")

def start(update, context):
    update.message.reply_text("Schick mir Usernames (Text oder .txt-Datei). Ich zeige dir nur die, die 100% frei sind ✅")

if __name__ == "__main__":
    print("🚀 Bot startet...")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, check_text))
    dp.add_handler(MessageHandler(Filters.document.mime_type("text/plain"), check_file))

    updater.start_polling()
    print("✅ Bot läuft (Polling aktiv)")
    updater.idle()
