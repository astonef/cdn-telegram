import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from io import BytesIO
from push_to_gh import upload_to_github
from auth import is_authorized
from utils import is_url_alive

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ Non sei autorizzato a usare questo bot")
        return

    logging.debug("🎥 Video ricevuto da utente ID: %s", update.message.from_user.id)

    await update.message.reply_text("🎬 Video in lavorazione...")

    try:
        video = update.message.video
        logging.debug(f"🎞️ update.message.video: {video}")

        file = await video.get_file()
        logging.debug("📁 File Telegram ottenuto: %s", file.file_path)

        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".mp4"
        filepath = os.path.join(os.getcwd(), filename)
        logging.debug("📝 Nome file: %s", filename)
        logging.debug("📍 Percorso: %s", filepath)

        bio = BytesIO()
        await file.download_to_memory(out=bio)
        logging.debug("📥 Download in memoria completato (%d bytes)", len(bio.getvalue()))

        with open(filepath, "wb") as f:
            f.write(bio.getvalue())
        logging.debug("✅ Video salvato localmente")

    except Exception as e:
        logging.error(f"❌ Errore nel download video: {e}")
        await update.message.reply_text("Errore nel download del video 🎥")
        return

    status, response = upload_to_github(filepath, f"video/{filename}")
    logging.debug(f"🚀 Upload status: {status}, response: {response}")

    if status in [200, 201]:
        cdn_js = f"https://cdn.jsdelivr.net/gh/astonef/fstfd-cdn@core/video/{filename}"
        cdn_stat = f"https://cdn.statically.io/gh/astonef/fstfd-cdn/core/video/{filename}"
        raw_url = f"https://raw.githubusercontent.com/astonef/fstfd-cdn/core/video/{filename}"

        cdn_url = cdn_js
        alive = await is_url_alive(cdn_url)
        logging.debug(f"🔍 jsDelivr alive: {alive}")

        if not alive:
            logging.warning("⚠️ jsDelivr fallito, provo Statically")
            cdn_url = cdn_stat
            alive = await is_url_alive(cdn_url)
            logging.debug(f"🔍 Statically alive: {alive}")

        link_id = filename.replace(".mp4", "")
        context.bot_data[link_id] = cdn_url if alive else raw_url

        buttons = [
            [InlineKeyboardButton("📋 LINK VIDEO", callback_data=f"copy::{link_id}")],
            [InlineKeyboardButton("🗑️ ELIMINA MESSAGGIO", callback_data="delete_msg")]
        ]

        if alive:
            buttons.insert(0, [InlineKeyboardButton("▶️ APRI VIDEO", url=cdn_url)])
        else:
            buttons.insert(0, [InlineKeyboardButton("🛟 Backup (GitHub Raw)", url=raw_url)])

        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("✅ Video caricato", reply_markup=keyboard)
        logging.debug("📤 Messaggio di conferma inviato")

    else:
        logging.error(f"❌ Upload fallito: {response.get('message')}")
        await update.message.reply_text("Errore nell’upload 🚫")

    try:
        os.remove(filepath)
        logging.debug(f"🧹 File rimosso: {filepath}")
    except Exception as e:
        logging.warning(f"⚠️ Impossibile rimuovere il file: {e}")
