from telegram.ext import CallbackContext
from telegram import Update
from . import config

async def broadcast(update: Update, context: CallbackContext):
    admin_id = update.effective_user.id
    if str(admin_id) not in {"8019666279"}:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    await update.message.reply_text("📢 Send the message you want to broadcast:")
    context.user_data["awaiting_broadcast"] = True
