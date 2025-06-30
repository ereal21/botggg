from telegram.ext import CallbackContext
from telegram import Update
from . import config

async def handle_broadcast(update: Update, context: CallbackContext):
    if not context.user_data.get("awaiting_broadcast"):
        return False
    context.user_data["awaiting_broadcast"] = False
    message_to_send = update.message
    try:
        with open(r"C:\\Users\\eriku\\Desktop\\TGBot\\USERIDS.txt", "r") as f:
            user_ids = [int(line.strip()) for line in f if line.strip()]
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to read user list: {e}")
        return True
    success = 0
    for uid in user_ids:
        try:
            await context.bot.copy_message(chat_id=uid, from_chat_id=update.effective_chat.id, message_id=message_to_send.message_id)
            success += 1
        except Exception as e:
            config.logger.warning(f"Failed to send to {uid}: {e}")
    await update.message.reply_text(f"✅ Broadcast sent to {success} users.")
    return True
