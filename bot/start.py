from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import CallbackContext
from . import config
from .subscriptions import has_active_subscription

async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or ""
    user_id = str(update.effective_user.id)
    lang = context.user_data.get("lang", "en")
    plan = "Active" if has_active_subscription(username) else "None"
    balance = config.user_balances.get(username, 0.0)
    try:
        file_path = r"C:\\Users\\eriku\\Desktop\\TGBot\\USERIDS.txt"
        with open(file_path, "r+") as f:
            ids = {line.strip() for line in f}
            if user_id not in ids:
                f.write(f"{user_id}\n")
    except Exception as e:
        config.logger.warning(f"Could not log user ID: {e}")

    welcome_text = config.translations.get(lang, config.translations['en'])['welcome'].format(
        username=username, plan=plan, balance=f"{balance:.2f}"
    )
    keyboard = [
        [InlineKeyboardButton(config.translations[lang]['search_button'], callback_data="search")],
        [InlineKeyboardButton(config.translations[lang]['shop_button'], callback_data="topup"), InlineKeyboardButton(config.translations[lang]['profile_button'], callback_data="profile")],
        [InlineKeyboardButton(config.translations[lang]['reviews_button'], callback_data="reviews"), InlineKeyboardButton(config.translations[lang]['language_button'], callback_data="language")],
    ]
    try:
        with open(r"E:\\a\\animbanner.mp4", "rb") as video:
            await context.bot.send_video(chat_id=chat_id, video=video)
    except Exception as e:
        config.logger.error(f"Failed to send welcome video: {e}")
    await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
