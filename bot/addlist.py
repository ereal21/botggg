from telegram.ext import CallbackContext
from telegram import Update
from . import config

async def addlist(update: Update, context: CallbackContext):
    user = update.effective_user.username or ""
    if user not in config.ADMIN_USERS:
        await update.message.reply_text("❌ You don't have permission to add users.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addlist @username")
        return
    new_user = context.args[0].lstrip("@")
    config.ACCESS_USERS.add(new_user)
    await update.message.reply_text(f"✅ User @{new_user} added to access list.")
