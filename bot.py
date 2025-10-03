from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import os
import tempfile
import pandas as pd

TOKEN = os.getenv("BOT_TOKEN")

def check_username(uname: str) -> str:
    tg_url = f"https://t.me/{uname}"
    frag_url = f"https://fragment.com/username/{uname}"

    try:
        r = requests.get(tg_url, allow_redirects=True, timeout=5)
        html = r.text.lower()
    except:
        return "⚠️ Fehler"

    # Frei?
    if r.status_code == 404 or "username not occupied" in html:
        frag = requests.get(frag_url, timeout=5)
        if "auction" in frag.text.lower() or "lot" in frag.text.lower():
            return "💸 Fragment"
        else:
            return "✅ Frei"

    # Vergeben
    if "if you have telegram, you can contact" in html:
        return "❌ Vergeben"

    # Banned oder ungültig
    if "this username is not available" in html or "invalid invite link" in html:
        return "🚫 Banned"

    # Fallback
    return "❌ Vergeben"

def format_results(data):
    free = [f"@{d['username']}" for d in data if d['status'] == "✅ Frei"]
    frag = [f"@{d['username']}" for d in data if d['status'] == "💸 Fragment"]
    taken = [f"@{d['username']}" for d in data if d['status'] == "❌ Vergeben"]
    banned = [f"@{d['username']}" for d in data if d['status'] == "🚫 Banned"]

    msg = []
    if free: msg.append("✅ Frei:\n" + " ".join(free))
    if frag: msg.append("💸 Fragment:\n" + " ".join(frag))
    if taken: msg.append("❌ Vergeben:\n" + " ".join(taken))
    if banned: msg.append("🚫 Banned:\n" + " ".join(banned))
    return "\n\n".join(msg) if msg else "Keine Ergebnisse."

def check_text(update, context):
    usernames = [u.strip("@").lower() for u in update.message.text.split() if len(u) >= 4]
    data = [{"username": u, "status": check_username(u)} for u in usernames]
    update.message.reply_text(format_results(data))

def check_file(update, context):
    file = update.message.document.get_file()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        file.download(custom_path=tmp.name)
        with open(tmp.name, "r", encoding="utf-8") as f:
            usernames = [line.strip().lower().replace("@", "") for line in f if line.strip()]

    data = [{"username": u, "status": check_username(u)} for u in usernames]

    # CSV speichern
    df = pd.DataFrame(data)
    out_path = tempfile.mktemp(suffix=".csv")
    df.to_csv(out_path, index=False, encoding="utf-8")

    # Ergebnisse im Chat + Datei
    update.message.reply_text(format_results(data))
    with open(out_path, "rb") as f:
        update.message.reply_document(f, filename="results.csv", caption="Hier die CSV mit allen Ergebnissen ✅")

def start(update, context):
    update.message.reply_text("Schick mir Usernames (Text oder .txt-Datei).")

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
