import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.ext import CommandHandler
from dotenv import load_dotenv
from push_to_gh import upload_to_github
from handler_start_user_id import handle_start
from auth import is_authorized
from io import BytesIO
from aiohttp import web
import asyncio
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

async def is_url_alive(url: str, retries: int = 3, delay: float = 2) -> bool:
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        return True
        except Exception as e:
            logging.warning(f"⚠️ Tentativo {attempt+1} fallito: {e}")
    return False

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("⛔ Non sei autorizzato a usare questo bot")
        return

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

        cdn_js = f"https://cdn.jsdelivr.net/gh/astonef/fstfd-cdn@core/images/{filename}"
        cdn_stat = f"https://cdn.statically.io/gh/astonef/fstfd-cdn/core/images/{filename}"
        raw_url = f"https://raw.githubusercontent.com/astonef/fstfd-cdn/core/images/{filename}"

        cdn_url = cdn_js
        alive = await is_url_alive(cdn_url, retries=3)
        if not alive:
            logging.warning("❌ jsDelivr fallito, provo Statically")
            cdn_url = cdn_stat
            alive = await is_url_alive(cdn_url, retries=2)

        link_id = filename.replace(".jpg", "")
        context.bot_data[link_id] = cdn_url if alive else raw_url

        buttons = [
            [InlineKeyboardButton("📋 OTTIENI IL LINK IN CHAT", callback_data=f"copy::{link_id}")]
        ]

        if alive:
            buttons.insert(0, [InlineKeyboardButton("📡 APRI IMMAGINE NEL BROWSER", url=cdn_url)])
        else:
            buttons.insert(0, [InlineKeyboardButton("🛟 Backup (GitHub Raw)", url=raw_url)])

        buttons.append([InlineKeyboardButton("🗑️ ELIMINA MESSAGGIO IN CHAT", callback_data="delete_msg")])
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

async def handle_copy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data.startswith("copy::"):
        link_id = data.replace("copy::", "")
        url = context.bot_data.get(link_id)
        if url:
            await update.callback_query.answer("✅ Link copiabile inviato", show_alert=False)
            await update.effective_chat.send_message(url)
        else:
            await update.callback_query.answer("⚠️ Link non trovato", show_alert=True)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("mio_id", handle_start))
app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.add_handler(CallbackQueryHandler(handle_delete_callback, pattern="delete_msg"))
app.add_handler(CallbackQueryHandler(handle_copy_callback, pattern="^copy::"))




async def handle_ping(request):
    return web.Response(text="✅ Bot attivo", status=200)

app_web = web.Application()
app_web.router.add_get("/ping", handle_ping)

async def main():
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=10000)
    await site.start()

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
