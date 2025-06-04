from telegram import Update
from telegram.ext import ContextTypes
from auth import is_authorized

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"👤 Il tuo Telegram ID è: {user_id}")

    if is_authorized(user_id):
        await update.message.reply_text("✅ Sei autorizzato! Invia un'immagine.")
    else:
        await update.message.reply_text("⛔ Non sei autorizzato! Contatta l'amministratore.")
        

