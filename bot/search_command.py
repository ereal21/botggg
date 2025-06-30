import time
from datetime import datetime
from telegram.ext import CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from . import config
from .subscriptions import has_active_subscription, time_until_next_search

async def search_command(update: Update, context: CallbackContext):
    user = update.effective_user.username or ""
    chat_id = update.effective_chat.id

    if chat_id in config.search_in_progress or context.user_data.get("awaiting_query"):
        await update.message.reply_text("❌ Please wait until your current search finishes.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /search <query>")
        return

    query = " ".join(context.args).strip()
    if len(query) < 2 or query.lower() in {tok.lower() for tok in config.BANNED_TOKENS}:
        await update.message.reply_text("❌ Your query is not valid.")
        return

    is_subscribed = has_active_subscription(user)
    is_access = user in config.ACCESS_USERS

    if not is_subscribed and is_access:
        remaining = time_until_next_search(user)
        if remaining > 0:
            hours = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            sub_expiry = datetime.utcfromtimestamp(config.user_subscriptions.get(user, 0)).strftime('%Y-%m-%d %H:%M:%S UTC')
            await update.message.reply_text(
                f"⏳ You are on cooldown. Next search available in {hours}h {mins}m.\n"
                f"💳 Subscription required to receive results.\n"
                f"📅 Subscription expires: `{sub_expiry}`" if user in config.user_subscriptions else "📅 You don’t have an active subscription.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Top Up", callback_data="topup")]])
            )
            return
        config.search_cooldowns[user] = time.time()

    context.user_data["awaiting_query"] = False
    if user not in config.ACCESS_USERS:
        if not has_active_subscription(user, config.SEARCH_COST):
            await update.message.reply_text(f"❌ You need at least ${config.SEARCH_COST} in balance. Use /topup to add.")
            return
        config.user_balances[user] = config.user_balances.get(user, 0.0) - config.SEARCH_COST
    context.user_data["prompt_id"] = None
    config.search_in_progress.add(chat_id)
    fmt = context.user_data.get("result_format", "txt")
    max_mb = context.user_data.get("max_size_mb", config.MAX_UPLOAD // (1024*1024))
    pos = config.search_queue.qsize() + 1
    await update.message.reply_text(
        f"🔎 Searching for `{query}` with .{fmt} up to {max_mb} MB…\n[{'░'*10}] 0% (Est. {pos*10}s)",
        parse_mode="Markdown"
    )
    await config.search_queue.put((chat_id, query, None, user))
    config.logger.info(f"Queued search via command `{query}`")
