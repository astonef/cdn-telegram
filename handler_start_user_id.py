from telegram.ext import CommandHandler
from telegram import Update

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"👤 Il tuo Telegram ID è: {user_id}")


