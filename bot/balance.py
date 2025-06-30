from telegram.ext import CallbackContext
from telegram import Update
from . import config

async def balance_cmd(update: Update, context: CallbackContext):
    user = update.effective_user.username or str(update.effective_user.id)
    bal = config.user_balances.get(user, 0.0)
    await update.message.reply_text(f"💰 Your balance: ${bal:.2f}")
