from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from . import config

def get_search_menu(context, lang):
    """Return (text, keyboard) for the Search menu, showing current selections."""
    q = context.user_data.get("query")
    fmt = context.user_data.get("result_format", "txt")
    size = context.user_data.get("max_size_mb")

    btn1 = InlineKeyboardButton(
        f"📝 Query: {q}" if q else "📝 Enter Query",
        callback_data="search_menu_query",
    )
    btn2 = InlineKeyboardButton(
        f"🗃️ Format: .{fmt}" if fmt else "🗃️ Select Format",
        callback_data="search_menu_format",
    )
    btn3 = InlineKeyboardButton(
        f"📥 Size: {size} MB" if size else "📥 Set Max Size",
        callback_data="search_menu_size",
    )
    btn4 = InlineKeyboardButton("🏠 Home", callback_data="back_to_main")

    keyboard = [[btn1], [btn2], [btn3], [btn4]]
    text = (
        "🔎 *Search Menu*\n\n"
        "📝 Enter or change your query keyword.\n"
        "🗃️ Choose the format for results (txt,rar).\n"
        "📥 Specify the maximum file size for the results (1–19 MB).\n\n"
        "Please choose an option:"
    )
    return text, InlineKeyboardMarkup(keyboard)
