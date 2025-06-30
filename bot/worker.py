import asyncio
import math
import os
import zipfile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application
from . import config

async def search_worker(app: Application):
    while True:
        chat_id, query, prompt_id, user_label, fmt, max_mb = await config.search_queue.get()
        config.logger.info(f"🔎 Search requested by {user_label}: '{query}'")
        if prompt_id:
            try:
                await app.bot.delete_message(chat_id=chat_id, message_id=prompt_id)
            except Exception:
                pass
        status = await app.bot.send_message(
            chat_id=chat_id,
            text=f"🔎 Searching for `{query}`…",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Stop", callback_data="stop_search")]])
        )
        status_id = status.message_id
        try:
            proc = await asyncio.create_subprocess_exec(
                config.SEARCHER_BIN, "--index", config.TANTIVY_INDEX, "--query", query,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            config.running_search_process[chat_id] = proc
        except Exception as e:
            await app.bot.edit_message_text(chat_id=chat_id, message_id=status_id, text=f"❌ Failed to launch searcher: {e}")
            config.search_in_progress.discard(chat_id)
            continue
        await proc.wait()
        config.search_in_progress.discard(chat_id)
