import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
from push_to_gh import upload_to_github
from io import BytesIO
import aiohttp

# logging setup
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("cdn-telegram_debug.log", mode="a", encoding="utf-8"),
    ]
)

async def is_url_alive(url: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                return resp.status == 200
    except Exception as e:
        logging.warning(f"⚠️ CDN check failed: {e}")
        return False

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.debug("📨 Messaggio ricevuto")

    if update.message.caption:
        logging.debug("🟡 Caption presente, immagine ignorata")
        return

    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        filepath = os.path.join(os.getcwd(), filename)

        logging.debug(f"📁 filename: {filename}")
        logging.debug(f"📍 filepath: {filepath}")
        logging.debug(f"🔍 file: {file}")
        logging.debug(f"🌐 file.file_path: {file.file_path}")

        bio = BytesIO()
        await file.download_to_memory(out=bio)

        with open(filepath, "wb") as f:
            f.write(bio.getvalue())

        logging.debug("✅ Download completato")

    except Exception as e:
        logging.error(f"❌ Errore nel download: {e}")
        await update.message.reply_text("Errore nel download 📥")
        return

    status, response = upload_to_github(filepath, f"images/{filename}")

    if status in [200, 201]:
        logging.info(f"✅ Upload riuscito: {filename}")

        try:
            await update.message.delete()
            logging.debug("🗑️ Messaggio utente cancellato")
        except Exception as e:
            logging.warning(f"⚠️ Errore cancellazione messaggio: {e}")

        cdn_url = f"https://cdn.statically.io/gh/astonef/fstfd-cdn/core/images/{filename}"
        raw_url = f"https://raw.githubusercontent.com/astonef/fstfd-cdn/core/images/{filename}"

        try:
            alive = await is_url_alive(cdn_url)
            logging.debug(f"🌐 CDN online: {alive}")
        except Exception as e:
            alive = False
            logging.warning(f"⚠️ CDN check fallito: {e}")

        buttons = []
        if alive:
            buttons.append([InlineKeyboardButton("🔗 CDN (Statically)", url=cdn_url)])
        buttons.append([InlineKeyboardButton("🛟 Backup (GitHub Raw)", url=raw_url)])
        buttons.append([InlineKeyboardButton("🗑️ Elimina messaggio", callback_data="delete_msg")])
        keyboard = InlineKeyboardMarkup(buttons)

        user = update.message.from_user.first_name or "utente"

        with open(filepath, "rb") as img:
            await update.message.chat.send_photo(
                photo=img,
                caption=f"✅ Immagine caricata da {user}",
                reply_markup=keyboard
            )

    else:
        logging.error(f"❌ Errore upload: {response.get('message')}")
        await update.message.reply_text(f"Errore ❌: {response.get('message')}")

    try:
        os.remove(filepath)
        logging.debug("🧹 File temporaneo rimosso")
    except Exception as e:
        logging.warning(f"⚠️ Impossibile cancellare {filepath}: {e}")

async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.callback_query.message.delete()
        logging.debug("🧽 Messaggio eliminato via bottone")
    except Exception as e:
        logging.warning(f"❌ Errore eliminazione da callback: {e}")

    await update.callback_query.answer()

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.add_handler(CallbackQueryHandler(handle_delete_callback, pattern="delete_msg"))
app.run_polling()

async def handle_ping(request):
    return web.Response(text="✅ Bot attivo", status=200)

# server HTTP per Render + UptimeRobot
app_web = web.Application()
app_web.router.add_get("/ping", handle_ping)

import asyncio
asyncio.create_task(web._run_app(app_web, port=10000))