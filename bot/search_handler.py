import asyncio
import math
import os
import zipfile
import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from . import config
from .handle_broadcast import handle_broadcast
from .menu import get_search_menu
from .subscriptions import has_active_subscription

async def handle_search(update: Update, context: CallbackContext):
    if await handle_broadcast(update, context):
        return
    user = update.effective_user.username or str(update.effective_user.id)
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    lang = context.user_data.get("lang", "en")

    if chat_id in config.search_in_progress:
        await update.message.reply_text("❌ Please wait until your current search finishes.")
        return

    if context.user_data.get("awaiting_query"):
        context.user_data["query"] = text
        context.user_data.pop("awaiting_query")
        msg, kb = config.translations[lang]['waiting_confirmation'], None
        await update.message.reply_text(msg, reply_markup=kb)
        return

    if context.user_data.get("awaiting_topup_amount"):
        try:
            amount = float(text)
        except ValueError:
            await update.message.reply_text("Please enter a valid number.")
            return
        context.user_data["topup_amount"] = amount
        context.user_data.pop("awaiting_topup_amount")
        kb = [
            [InlineKeyboardButton(m["label"], callback_data=f"topup_method_{k}")]
            for k, m in config.PAYMENT_METHODS.items()
        ]
        kb.append([InlineKeyboardButton("🏠 Home", callback_data="back_to_main")])
        await update.message.reply_text(
            config.translations[lang]['choose_payment_method'],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return

    if context.user_data.get("awaiting_size"):
        try:
            mb = int(text)
        except ValueError:
            await update.message.reply_text("Please enter a number between 1 and 19")
            return
        context.user_data["max_size_mb"] = min(19, max(1, mb))
        context.user_data.pop("awaiting_size")
        menu_text, kb = get_search_menu(context, lang)
        await update.message.reply_text(menu_text, parse_mode="Markdown", reply_markup=kb)
        return

    query = context.user_data.get("query")
    if not query:
        await update.message.reply_text("❌ Please use /search <keyword> first.")
        return

    fmt = context.user_data.get("result_format", "txt")
    max_mb = context.user_data.get("max_size_mb", config.MAX_UPLOAD // (1024*1024))

    if user not in config.ACCESS_USERS:
        if not has_active_subscription(user, config.SEARCH_COST):
            await update.message.reply_text(f"❌ You need at least ${config.SEARCH_COST} in balance. Use /topup to add.")
            return
        config.user_balances[user] = config.user_balances.get(user, 0.0) - config.SEARCH_COST

    config.search_in_progress.add(chat_id)
    await config.search_queue.put((chat_id, query, context.user_data.get("prompt_id"), user, fmt, max_mb))
