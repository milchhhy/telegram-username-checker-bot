from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import os
import tempfile
import pandas as pd
import re

TOKEN = os.getenv("BOT_TOKEN")

def check_username(uname: str) -> str:
    tg_url = f"https://t.me/{uname}"
    frag_url = f"https://fragment.com/username/{uname}"

    try:
        r = requests.get(tg_url, allow_redirects=True, timeout=5)
        html = r.text.lower()
    except Exception as e:
        return f"⚠️ Fehler: {e}"

    # ❌ Vergeben → Profil mit Bild oder Beschreibung
    if "og:image" in html and "t_logo_2x.png" not in html:
        return "❌ Vergeben"
    if "property=\"og:description\" content=" in html and 'content=""' not in html:
        return "❌ Vergeben"

    # ⚪ oder 💸
    if 'property="og:description" content=""' in html and "t_logo_2x.png" in html:
        try:
            frag = requests.get(frag_url, timeout=5)
            frag_html = frag.text

            # --- Preis robust suchen ---
            price_match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*ton", frag_html, re.IGNORECASE)
            if not price_match:
                # auch wenn TON in eigenem <span> steht
                price_match = re.search(
                    r"([0-9]+(?:[.,][0-9]+)?)\s*(?:<[^>]+>\s*)*ton",
                    frag_html,
                    re.IGNORECASE
                )
            if not price_match:
                # Klassen wie lot-price / amount
                price_match = re.search(
                    r'(?:lot-price|amount|price)[^<]*?>\s*([0-9]+(?:[.,][0-9]+)?)',
                    frag_html,
                    re.IGNORECASE
                )

            price = price_match.group(1) + " TON" if price_match else None

            # --- Auction oder BuyNow ---
            if price:
                if re.search(r"auction|minimum bid|ending in", frag_html, re.IGNORECASE):
                    return f"💸 Fragment – Auction – {price}"
                if re.search(r"buy now|fixed price", frag_html, re.IGNORECASE):
                    return f"💸 Fragment – Buy Now – {price}"

            # Kein Preis / Unavailable → kein Fragment
            if re.search(r"unavailable|not for sale|unknown", frag_html, re.IGNORECASE):
                return "⚪ Verfügbar/Banned"

        except:
            return "⚪ Verfügbar/Banned"

        return "⚪ Verfügbar/Banned"

    return "⚠️ Unbekannt"


def check_text(update, context):
    usernames = [u.strip("@").lower() for u in update.message.text.split() if len(u) >= 4]
    data = [{"username": u, "status": check_username(u)} for u in usernames]

    available = [f"@{d['username']}" for d in data if d['status'].startswith("⚪")]
    frag = [f"@{d['username']} ({d['status']})" for d in data if d['status'].startswith("💸")]
    taken = [f"@{d['username']}" for d in data if d['status'] == "❌ Vergeben"]

    msg = []
    if available: msg.append("⚪ Verfügbar/Banned:\n" + " ".join(available))
    if frag: msg.append("💸 Fragment:\n" + "\n".join(frag))
    if taken: msg.append("❌ Vergeben:\n" + " ".join(taken))

    update.message.reply_text("\n\n".join(msg) if msg else "Keine Ergebnisse.")


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

    available = [f"@{d['username']}" for d in data if d['status'].startswith("⚪")]
    frag = [f"@{d['username']} ({d['status']})" for d in data if d['status'].startswith("💸")]
    taken = [f"@{d['username']}" for d in data if d['status'] == "❌ Vergeben"]

    msg = []
    if available: msg.append("⚪ Verfügbar/Banned:\n" + " ".join(available))
    if frag: msg.append("💸 Fragment:\n" + "\n".join(frag))
    if taken: msg.append("❌ Vergeben:\n" + " ".join(taken))

    update.message.reply_text("\n\n".join(msg) if msg else "Keine Ergebnisse.")
    with open(out_path, "rb") as f:
        update.message.reply_document(f, filename="results.csv", caption="CSV mit allen geprüften Usernames")


def start(update, context):
    update.message.reply_text(
        "Schick mir Usernames (Text oder .txt-Datei).\n"
        "Kategorien:\n"
        "⚪ Verfügbar oder Banned\n"
        "💸 Fragment (zeigt Preis & Auction/Buy Now)\n"
        "❌ Vergeben"
    )


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
