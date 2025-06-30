from threading import Thread
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from . import config
from .start import start
from .addlist import addlist
from .broadcast import broadcast
from .balance import balance_cmd
from .topup import topup_cmd
from .callback import button_callback
from .search_handler import handle_search
from .post_init import post_init


def main():
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    config.telegram_app = app
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addlist", addlist))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("topup", topup_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    Thread(target=lambda: config.app_web.run(port=5000)).start()
    app.run_polling()
