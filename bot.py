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
    except Exception as e:
        return f"⚠️ Fehler: {e}"

    # 🚫 Banned
    if "this username is not available" in html:
        return "🚫 Banned"

    # 💸 Fragment prüfen nur wenn nicht banned
    try:
        frag = requests.get(frag_url, timeout=5)
        frag_html = frag.text.lower()
        if "auction" in frag_html or "lot" in frag_html:
            return "💸 Fragment"
    except:
        pass

    # ✅ Frei (Contact-Seite ohne zusätzliche Infos)
    if f"telegram: contact @{uname}".lower() in html and "tgme_page_extra" not in html and "tgme_page_description" not in html:
        return "✅ Frei"

    # ❌ Vergeben (Infos vorhanden)
    if "tgme_page_description" in html or "tgme_page_extra" in html:
        return "❌ Vergeben"

    return "⚠️ Unbekannt"

def check_text(update, context):
    usernames = [u.strip("@").lower() for u in update.message.text.split() if len(u) >= 4]
    results = [f"@{u}: {check_username(u)}" for u in usernames]
    update.message.reply_text("\n".join(results))

def check_file(update, context):
    file = update.message.document.get_file()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        file.download(custom_path=tmp.name)
        with open(tmp.name, "r", encoding="utf-8") as f:
            usernames = [line.strip().lower().replace("@", "") for line in f if line.strip()]

    data = [{"username": u, "status": check_username(u)} for u in usernames]

    df = pd.DataFrame(data)
    out_path = tempfile.mktemp(suffix=".csv")
    df.to_csv(out_path, index=False, encoding="utf-8")

    msg = "\n".join([f"@{d['username']}: {d['status']}" for d in data])
    update.message.reply_text(msg if msg else "Keine Ergebnisse.")
    with open(out_path, "rb") as f:
        update.message.reply_document(f, filename="results.csv", caption="CSV mit allen geprüften Usernames")

def debug(update, context):
    if not context.args:
        update.message.reply_text("Nutze: /debug <username>")
        return
    uname = context.args[0].strip("@").lower()
    tg_url = f"https://t.me/{uname}"
    r = requests.get(tg_url, allow_redirects=True, timeout=5)

    snippet = r.text[:800]  # ersten 800 Zeichen anzeigen
    update.message.reply_text(f"Status: {r.status_code}\nSnippet:\n{snippet}")

def start(update, context):
    update.message.reply_text("Schick mir Usernames (Text oder .txt-Datei).\nNutze /debug <username> für HTML-Snippets.")

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
