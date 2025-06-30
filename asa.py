import io
import time
import logging
import zipfile
import subprocess
import html
import os
import asyncio
import requests
import qrcode
import random
import math
from datetime import datetime
from flask import Flask, request, jsonify
import nowpayments
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_search_menu(context, lang):
    """Return (text, keyboard) for the Search menu, showing current selections."""
    q     = context.user_data.get("query")
    fmt   = context.user_data.get("result_format", "txt")
    size  = context.user_data.get("max_size_mb")

    btn1 = InlineKeyboardButton(
        f"📝 Query: {q}" if q else "📝 Enter Query",
        callback_data="search_menu_query"
    )
    btn2 = InlineKeyboardButton(
        f"🗃️ Format: .{fmt}" if fmt else "🗃️ Select Format",
        callback_data="search_menu_format"
    )
    btn3 = InlineKeyboardButton(
        f"📥 Size: {size} MB" if size else "📥 Set Max Size",
        callback_data="search_menu_size"
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

def get_crypto_amount(usd_amount, coin_id):
    response = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={'ids': coin_id, 'vs_currencies': 'usd'}
    )
    response.raise_for_status()
    price_data = response.json()
    crypto_price = price_data[coin_id]['usd']
    return usd_amount / crypto_price

def has_active_subscription(username: str, cost: float = 0.0) -> bool:
    if not username:
        return False
    if username in ACCESS_USERS:
        return True
    return user_balances.get(username, 0.0) >= cost
def time_until_next_search(username: str) -> float:
    last_time = search_cooldowns.get(username, 0)
    return max(0, COOLDOWN_HOURS * 3600 - (time.time() - last_time))
# ======== Logger definition ========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

NP_CLIENT = nowpayments.Client(api_key=os.getenv("NOWPAYMENTS_API_KEY"))
WEBHOOK_URL = os.getenv("NGROK_URL", "") + "/nowpayments-webhook"
app_web = Flask(__name__)
@app_web.route("/nowpayments-webhook", methods=["POST"])
def nowpayments_ipn():
    data = request.get_json()
    invoice_id = data.get("invoice_id")
    order_id = data.get("order_id")
    status = data.get("payment_status")
    amount_usd = data.get("price_amount")
    username = order_id.split(":")[0] if order_id else ""
    if status == "confirmed":
        user_balances[username] = user_balances.get(username, 0.0) + float(amount_usd)
    return jsonify({"status": "ok"})
# ======== Configuration ========
BOT_TOKEN = os.getenv("BOT_TOKEN", 
"7932293544:AAGw8UmQ5pdwC0Bi28690yIczmoq3IIk7fg")
SEARCHER_BIN = r"B:\Indexing\tantivy_searcher\tantivy_searcher\target\release\tantivy_searcher.exe"
TANTIVY_INDEX = r"Z:\as"

ACCESS_USERS = {"Inereal", "Penguinite", "KN0O7" , "CoreyD6" , "Kqizen"}
ADMIN_USERS = {"Inereal"}

# Only exact-match queries are forbidden
BANNED_TOKENS = [
    "www.", "https://", "http://", ".com", "com", "org", ".org", ".www", "://",
    "/", ":"
]

MAX_UPLOAD = 19 * 1024 * 1024  # 20 MB

SEARCH_COST = 1.0  # USD cost per search
SUBSCRIPTIONS = {
    "1_day":    {"label": "🪵 1 Day - $14.99",       "price": 14.99},
    "1_week":   {"label": "⚙️ 1 Week - $29.99",   "price": 29.99},
    "1_month":  {"label": "🥇 1 Month - $49.99",  "price": 49.99},
    "lifetime": {"label": "💎 Lifetime - $299.99","price": 299.99}
}

REQUEST_PASS_OPTIONS = {
    "1_day":    {"label": "🪵 1 Day Search Pass - $9.99",   "price": 9.99},
    "3_days":   {"label": "⚙️ 3 Days Search Pass - $19.99",  "price": 19.99},
    "7_days":   {"label": "🥇 1 Week Search Pass - $29.99",  "price": 29.99},
    "lifetime_days": {"label": "💎 Lifetime Days Search Pass - $199.99", "price": 199.99}
}

PAYMENT_METHODS = {
    "TRX":      {"label": "TRX",        "address": "TPEJo7aRMygzZx8etM5zFscESZiQyDz1eQ"},
    "SOL":      {"label": "Solana",     "address": "5Vs2WBx8gFQeFJsVC4zrAhiRKRiVBJEmm5uH1VJTNk1o"},
    "BTC":      {"label": "Bitcoin",    "address": "bc1qg2c3uygt6yyhzdsywq2kx838jtem4l7c9pejwj"},
    "ETH":      {"label": "ETH",        "address": "0x7190bB77Ea0a25eb94F38a4da3d75aa15F9BebfA"},
    "XRP":      {"label": "XRP",        "address": "rEnYhmqS5CT3SBFyxnbPNBmrKzcbLCa3it"},
    "TRXUSDT":  {"label": "USDT-TRC20", "address": "TPEJo7aRMygzZx8etM5zFscESZiQyDz1eQ"},
    "BNB":      {"label": "BNB",        "address": "0x7190bB77Ea0a25eb94F38a4da3d75aa15F9BebfA"},
    "LTC":      {"label": "Litecoin",   "address": "LYnmsU8Ht7DVT2JyQAh1GwmX5q6y1kuFMe"},
    "USDC_SOL": {"label": "USDC (SOL)", "address": "5Vs2WBx8gFQeFJsVC4zrAhiRKRiVBJEmm5uH1VJTNk1o"},
    "USDC_ETH": {"label": "USDC (ETH)", "address": "0x7190bB77Ea0a25eb94F38a4da3d75aa15F9BebfA"},
    "TON":      {"label": "TON",        "address": "0x7190bB77Ea0a25eb94F38a4da3d75aa15F9BebfA"},
}

COINGECKO_IDS = {
    "TRX":      "tron",        "SOL": "solana",    "BTC": "bitcoin",
    "ETH":      "ethereum",    "XRP": "ripple",    "TRXUSDT": "tether",
    "BNB":      "binancecoin", "LTC": "litecoin",  "USDC_SOL": "usd-coin",
    "USDC_ETH": "usd-coin",    "TON": "the-open-network",
    "BCH":      "bitcoin-cash","ETC": "ethereum-classic",
    "XMR":      "monero"
}

# ======== Translations ========
translations = {
    'en': {
        'welcome': (
            "👋 Welcome, @{username}!\n💰 Balance: {balance} EUR\n📝Plan: {plan}\n\n"
            "⚠️ Note: No refunds.\n💳 If the transacted amount is less than the required amount, the payment will not be confirmed. Please ensure you send the exact amount. Verify that your exchange provider does not deduct any sending fees. If you are unsure, it is advisable to send a slightly higher amount.\n\n"
            "_Experience the difference!_"
        ),
        'profile': "🎉 Your Profile\n\n👤 Plan: {plan}\n💰 Balance: {balance} EUR",
        'search_button': "🔎 Search",
        'shop_button': "🛒 Shop",
        'profile_button': "👤 Profile",
        'reviews_button': "⭐ Reviews",
        'language_button': "🌐 Language",
        'language_prompt': "🌐 Choose your language:",
        'plans_menu': "💳 *Plans*\nChoose an option:",
        'choose_subscription': "*Choose subscription plan:*",
        'choose_search_pass': "*Choose request pass:*",
        'waiting_confirmation': "⏳ *Waiting for payment confirmation...*\nPlease transfer the funds within 30 minutes.",
        'choose_payment_method': "*Choose payment method:*"
    },
    'es': {
        'welcome': (
            "👋 Bienvenido, @{username}!\n💰 Saldo: {balance} EUR\nPlan: {plan}\n\n"
            "⚠️ Nota: No hay reembolsos.\n💳 Si la cantidad transferida es menor que la requerida, el pago no será confirmado. Asegúrate de enviar la cantidad exacta. Verifica que tu proveedor de cambio no deduzca ninguna tarifa al enviar. Si no estás seguro, es recomendable enviar una cantidad ligeramente mayor.\n\n"
            "_¡Vive la diferencia!_"
        ),
        'profile': "🎉 Tu perfil\n\n👤 Plan: {plan}\n💰 Saldo: {balance} EUR",
        'search_button': "🔎 Buscar",
        'shop_button': "🛒 Tienda",
        'profile_button': "👤 Perfil",
        'reviews_button': "⭐ Reseñas",
        'language_button': "🌐 Idioma",
        'language_prompt': "🌐 Elige tu idioma:",
        'plans_menu': "💳 *Planes*\nElige una opción:",
        'choose_subscription': "*Elige un plan de suscripción:*",
        'choose_search_pass': "*Elige un pase de búsqueda:*",
        'waiting_confirmation': "⏳ *Esperando la confirmación del pago...*\nPor favor, transfiera los fondos dentro de 30 minutos.",
        'choose_payment_method': "*Elige el método de pago:*"
    },
    'pt': {
        'welcome': (
            "👋 Bem-vindo, @{username}!\n💰 Saldo: {balance} EUR\nPlano: {plan}\n\n"
            "⚠️ Atenção: Sem reembolsos.\n💳 Se o valor transacionado for menor do que o valor exigido, o pagamento não será confirmado. Por favor, envie o valor exato. Verifique se seu provedor de câmbio não deduz nenhuma taxa de envio. Se não tiver certeza, é aconselhável enviar um valor ligeiramente maior.\n\n"
            "_Sinta a diferença!_"
        ),
        'profile': "🎉 Seu perfil\n\n👤 Plano: {plan}\n💰 Saldo: {balance} EUR",
        'search_button': "🔎 Buscar",
        'shop_button': "🛒 Loja",
        'profile_button': "👤 Perfil",
        'reviews_button': "⭐ Avaliações",
        'language_button': "🌐 Idioma",
        'language_prompt': "🌐 Escolha seu idioma:",
        'plans_menu': "💳 *Planos*\nEscolha uma opção:",
        'choose_subscription': "*Escolha um plano de assinatura:*",
        'choose_search_pass': "*Escolha um passe de pesquisa:*",
        'waiting_confirmation': "⏳ *Aguardando confirmação de pagamento...*\nPor favor, transfira os fundos dentro de 30 minutos.",
        'choose_payment_method': "*Escolha o método de pagamento:*"
    },
    'ru': {
        'welcome': (
            "👋 Добро пожаловать, @{username}!\n💰 Баланс: {balance} EUR\nПлан: {plan}\n\n"
            "⚠️ Внимание: возврата средств не предусмотрено.\n💳 Если переведенная сумма меньше требуемой, платеж не будет подтвержден. Пожалуйста, отправьте точную сумму. Проверьте, не удерживает ли ваш обменник комиссию при отправке. Если вы не уверены, рекомендуется отправить немного больше.\n\n"
            "_Ощутите разницу!_"
        ),
        'profile': "🎉 Ваш профиль\n\n👤 План: {plan}\n💰 Баланс: {balance} EUR",
        'search_button': "🔎 Поиск",
        'shop_button': "🛒 Магазин",
        'profile_button': "👤 Профиль",
        'reviews_button': "⭐ Отзывы",
        'language_button': "🌐 Язык",
        'language_prompt': "🌐 Выберите язык:",
        'plans_menu': "💳 *Тарифы*\nВыберите опцию:",
        'choose_subscription': "*Выберите план подписки:*",
        'choose_search_pass': "*Выберите пропуск для поиска:*",
        'waiting_confirmation': "⏳ *Ожидание подтверждения оплаты...*\nПожалуйста, переведите средства в течение 30 минут.",
        'choose_payment_method': "*Выберите способ оплаты:*"
    },
    'zh': {
        'welcome': (
            "👋 欢迎, @{username}!\n💰 余额: {balance} EUR\n计划: {plan}\n\n"
            "⚠️ 注意: 不予退款。\n💳 如果交易金额少于所需金额，支付将无法确认。请确保您发送准确的金额。请确认您的兑换服务提供商不会扣除任何发送费用。如果不确定，建议多发送一些金额。\n\n"
            "_体验不同！_"
        ),
        'profile': "🎉 您的个人资料\n\n👤 计划: {plan}\n💰 余额: {balance} EUR",
        'search_button': "🔎 搜索",
        'shop_button': "🛒 商店",
        'profile_button': "👤 个人资料",
        'reviews_button': "⭐ 评论",
        'language_button': "🌐 语言",
        'language_prompt': "🌐 选择您的语言:",
        'plans_menu': "💳 *计划*\n选择一个选项:",
        'choose_subscription': "*选择订阅计划:*",
        'choose_search_pass': "*选择搜索通行证:*",
        'waiting_confirmation': "⏳ *等待付款确认...*\n请在30分钟内转账。",
        'choose_payment_method': "*选择付款方式:*"
    }
}

# Additional global structures
search_queue: asyncio.Queue = None
search_in_progress = set()
running_search_process = {}  # chat_id -> subprocess for search
canceled_searches = set()
search_cooldowns = {}
user_subscriptions = {}
COOLDOWN_HOURS = 4
user_balances = {}

async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or ""
    user_id = str(update.effective_user.id)
    lang = context.user_data.get("lang", "en")
    plan = "Active" if has_active_subscription(username) else "None"
    balance = 0.0

    # ✅ Save user ID to file if new
    try:
        file_path = r"C:\Users\eriku\Desktop\TGBot\USERIDS.txt"
        with open(file_path, "r+") as f:
            ids = {line.strip() for line in f}
            if user_id not in ids:
                f.write(f"{user_id}\n")
    except Exception as e:
        logger.warning(f"Could not log user ID: {e}")

    # ✅ Build welcome text before using it in caption
    welcome_text = translations.get(lang, translations['en'])['welcome'].format(
        username=username, plan=plan, balance=f"{balance:.2f}"
    )

    keyboard = [
        [InlineKeyboardButton("🔍 Search", callback_data="search")],
        [InlineKeyboardButton("🛒 Shop", callback_data="plans"),
         InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("⭐ Reviews", callback_data="reviews"),
         InlineKeyboardButton("🌐 Language", callback_data="language")]
    ]

    # ✅ Send .mp4 video with welcome text & full menu buttons
    try:
        with open(r"E:\a\animbanner.mp4", "rb") as video:
            await context.bot.send_video(chat_id=chat_id, video=video)
    except Exception as e:
        logger.error(f"Failed to send welcome video: {e}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
)



    welcome_text = translations.get(lang, translations['en'])['welcome'].format(
        username=username, plan=plan, balance=f"{balance:.2f}"
    )

    keyboard = [
        [InlineKeyboardButton(translations[lang]['search_button'], callback_data="search")],
        [
            InlineKeyboardButton(translations[lang]['shop_button'], callback_data="plans"),
            InlineKeyboardButton(translations[lang]['profile_button'], callback_data="profile")
        ],
        [
            InlineKeyboardButton(translations[lang]['reviews_button'], callback_data="reviews"),
            InlineKeyboardButton(translations[lang]['language_button'], callback_data="language")
        ]
    ]

async def addlist(update: Update, context: CallbackContext):
    user = update.effective_user.username or ""
    if user not in ADMIN_USERS:
        await update.message.reply_text("❌ You don't have permission to add users.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addlist @username")
        return
    new_user = context.args[0].lstrip("@")
    ACCESS_USERS.add(new_user)
    await update.message.reply_text(f"✅ User @{new_user} added to access list.")

async def search_command(update: Update, context: CallbackContext):
    user = update.effective_user.username or ""
    chat_id = update.effective_chat.id

    if chat_id in search_in_progress or context.user_data.get("awaiting_query"):
        await update.message.reply_text("❌ Please wait until your current search finishes.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /search <query>")
        return

    query = " ".join(context.args).strip()
    if len(query) < 2 or query.lower() in {tok.lower() for tok in BANNED_TOKENS}:
        await update.message.reply_text("❌ Your query is not valid.")
        return

    is_subscribed = has_active_subscription(user)
    is_access = user in ACCESS_USERS

    if not is_subscribed and is_access:
        remaining = time_until_next_search(user)
        if remaining > 0:
            hours = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            sub_expiry = datetime.utcfromtimestamp(user_subscriptions.get(user, 0)).strftime('%Y-%m-%d %H:%M:%S UTC')
            await update.message.reply_text(
                f"⏳ You are on cooldown. Next search available in {hours}h {mins}m.\n"
                f"💳 Subscription required to receive results.\n"
                f"📅 Subscription expires: `{sub_expiry}`" if user in user_subscriptions else "📅 You don’t have an active subscription.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 View Plans", callback_data="plans")]])
            )
            return
        # Start cooldown
        search_cooldowns[user] = time.time()

    context.user_data["awaiting_query"] = False
    if user not in ACCESS_USERS:
        if not has_active_subscription(user, SEARCH_COST):
            await update.message.reply_text(f"❌ You need at least ${SEARCH_COST} in balance. Use /topup to add.")
            return
        user_balances[user] = user_balances.get(user, 0.0) - SEARCH_COST
    context.user_data["prompt_id"] = None
    search_in_progress.add(chat_id)
    fmt = context.user_data.get("result_format", "txt")
    max_mb = context.user_data.get("max_size_mb", MAX_UPLOAD // (1024*1024))
    pos = search_queue.qsize() + 1
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔎 Searching for `{query}` with .{fmt} up to {max_mb} MB…\n[{'░'*10}] 0% (Est. {pos*10}s)",
        parse_mode="Markdown"
    )
    await search_queue.put((chat_id, query, None, user))
    logger.info(f"Queued search via command `{query}`")

async def broadcast(update: Update, context: CallbackContext):
    admin_id = update.effective_user.id
    if str(admin_id) not in {"8019666279"}:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    await update.message.reply_text("📢 Send the message you want to broadcast:")

    context.user_data["awaiting_broadcast"] = True

async def handle_broadcast(update: Update, context: CallbackContext):
    if not context.user_data.get("awaiting_broadcast"):
        return False

    context.user_data["awaiting_broadcast"] = False
    message_to_send = update.message

    try:
        with open(r"C:\Users\eriku\Desktop\TGBot\USERIDS.txt", "r") as f:
            user_ids = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    user_ids.append(int(line))
                except:
                    continue
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to read user list: {e}")
        return True

    success = 0
    for uid in user_ids:
        try:
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=update.effective_chat.id,
                message_id=message_to_send.message_id
            )
            success += 1
        except Exception as e:
            logger.warning(f"Failed to send to {uid}: {e}")

    await update.message.reply_text(f"✅ Broadcast sent to {success} users.")
    return True

async def balance_cmd(update: Update, context: CallbackContext):
    user = update.effective_user.username or str(update.effective_user.id)
    bal = user_balances.get(user, 0.0)
    await update.message.reply_text(f"💰 Your balance: ${bal:.2f}")

async def topup_cmd(update: Update, context: CallbackContext):
    if not context.args:
        return await update.message.reply_text("Usage: /topup <amount>")
    try:
        amount = float(context.args[0])
    except ValueError:
        return await update.message.reply_text("Invalid amount.")
    username = update.effective_user.username or str(update.effective_user.id)
    order_id = f"{username}:{random.randint(100000,999999)}"
    invoice = NP_CLIENT.create_invoice({
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "btc",
        "order_id": order_id,
        "ipn_callback_url": WEBHOOK_URL
    })
    await update.message.reply_text(
        f"*💸 Invoice Created*\n\nAmount: `{invoice.price_amount} {invoice.price_currency}`\n[Pay Here]({invoice.invoice_url})\n\n_You’ll be credited once payment is confirmed._",
        parse_mode="Markdown"
    )
async def button_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    data = q.data
    user = update.effective_user.username or ""
    chat_id = q.message.chat.id
    lang = context.user_data.get("lang", "en")

    if data == "stop_search":
        proc = running_search_process.get(chat_id)
        if proc:
            proc.kill()
            canceled_searches.add(chat_id)
            await q.edit_message_text("🛑 Search canceled.")
        else:
            await q.answer("No search in progress.", show_alert=True)
        return

    if data == "search":
        context.user_data.pop("awaiting_query", None)
        context.user_data.pop("awaiting_size", None)

        text, kb = get_search_menu(context, lang)
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        return

    if data == "search_menu_query":
        context.user_data["awaiting_query"] = True
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="search")]])
        await q.edit_message_text("🔎 Please send your search query or keyword now:", reply_markup=kb)
        return

    if data == "search_menu_format":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(".txt", callback_data="format_txt")],
            [InlineKeyboardButton(".rar", callback_data="format_rar")],
            [InlineKeyboardButton("← Back", callback_data="search")]
        ])
        await q.edit_message_text("📂 Select output format for results:", reply_markup=kb)
        return

    if data.startswith("format_"):
        fmt = data.split("_", 1)[1]
        context.user_data["result_format"] = fmt
        text, kb = get_search_menu(context, lang)
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        return

    if data == "search_menu_size":
        context.user_data["awaiting_size"] = True
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="search")]])
        await q.edit_message_text("📏 Send me the maximum file size in MB (1–19):", reply_markup=kb)
        return

    elif data == "profile":
        plan = "Active" if has_active_subscription(user) else "None"
        balance = 0.00
        profile_text = translations[lang]['profile'].format(plan=plan, balance=f"{balance:.2f}")
        await q.edit_message_text(
            profile_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="back_to_main")]])
        )

    elif data == "reviews":
        await q.edit_message_text(
            text="⭐ *Reviews*\n\nCheck out user feedback below:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 View Reviews", url="https://t.me/InerealReputation")],
                [InlineKeyboardButton("← Back", callback_data="back_to_main")]
            ])
        )

    elif data == "language":
        buttons = [
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
             InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es")],
            [InlineKeyboardButton("🇵🇹 Português", callback_data="lang_pt"),
             InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇨🇳 简体中文", callback_data="lang_zh")],
            [InlineKeyboardButton("← Back", callback_data="back_to_main")]
        ]

        await q.edit_message_text(
            translations[lang]['language_prompt'],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        context.user_data["lang"] = new_lang
        plan = "Active" if has_active_subscription(user) else "None"
        balance = 0.00
        welcome_text = translations[new_lang]['welcome'].format(
            username=user, plan=plan, balance=f"{balance:.2f}"
        )
        keyboard = [
            [InlineKeyboardButton(translations[new_lang]['search_button'], callback_data="search"),
             InlineKeyboardButton(translations[new_lang]['shop_button'], callback_data="plans")],
            [InlineKeyboardButton(translations[new_lang]['profile_button'], callback_data="profile"),
             InlineKeyboardButton(translations[new_lang]['reviews_button'], callback_data="reviews")],
            [InlineKeyboardButton(translations[new_lang]['language_button'], callback_data="language")]
        ]
        await q.edit_message_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "plans":
        await q.edit_message_text(
            translations[lang]['plans_menu'],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("☁️ Private cloud Plans", callback_data="choose_subscription")],
                [InlineKeyboardButton("🔍 Request Passes", callback_data="choose_search_pass")],
                [InlineKeyboardButton("← Back", callback_data="back_to_main")]
            ])
        )

    elif data == "choose_subscription":
        await q.edit_message_text(
            translations[lang]['choose_subscription'],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                *[
                    [InlineKeyboardButton(plan["label"], callback_data=f"buy_{key}")]
                    for key, plan in SUBSCRIPTIONS.items()
                ],
                [InlineKeyboardButton("← Back", callback_data="plans")]
            ])
        )

    elif data == "choose_search_pass":
        await q.edit_message_text(
            translations[lang]['choose_search_pass'],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                *[
                    [InlineKeyboardButton(pass_["label"], callback_data=f"buy_{key}")]
                    for key, pass_ in REQUEST_PASS_OPTIONS.items()
                ],
                [InlineKeyboardButton("← Back", callback_data="plans")]
            ])
        )
    elif data == "cancel_payment":
        plan_type, plan_key = context.user_data.get("pending_plan", (None, None))
        back_cb = "choose_subscription" if plan_type == "subscription" else "choose_search_pass"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(PAYMENT_METHODS[m]["label"], callback_data=f"pay_{m}")]
            for m in PAYMENT_METHODS
        ] + [[InlineKeyboardButton("← Back", callback_data=back_cb)]])

        # Try editing current message, fallback to new if fails
        try:
            await q.edit_message_text(
                text=translations[lang]['choose_payment_method'],
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Edit failed, sending fresh message instead: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=translations[lang]['choose_payment_method'],
                parse_mode="Markdown",
                reply_markup=keyboard
            )

    elif data == "confirm_paid":
        username = q.from_user.username or q.from_user.first_name
        await q.answer("✅ We've notified the admin.", show_alert=True)
        await context.bot.send_message(
            chat_id=-1002361956797,
            text=f"🧾 User [@{username}](https://t.me/{username}) pressed *I Paid* button.",
            parse_mode="Markdown"
        )

    elif data.startswith("admin_confirm_"):
        user_id = data.split("_")[-1]
        await q.answer("✅ Confirmed.")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Running `/addlist @{user_id}`..."
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"/addlist @{user_id}"
        )

    elif data.startswith("buy_"):
        plan_key = data.split("_", 1)[1]
        # first check passes, then subscriptions
        if plan_key in REQUEST_PASS_OPTIONS:
            context.user_data["pending_plan"] = ("pass", plan_key)
            await q.edit_message_text(
                translations[lang]['choose_payment_method'],
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    *[[InlineKeyboardButton(PAYMENT_METHODS[c]["label"], callback_data=f"pay_{c}")]
                      for c in PAYMENT_METHODS],
                    [InlineKeyboardButton("← Back", callback_data="choose_search_pass")]
                ])
            )
        elif plan_key in SUBSCRIPTIONS:
            context.user_data["pending_plan"] = ("subscription", plan_key)
            await q.edit_message_text(
                translations[lang]['choose_payment_method'],
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    *[[InlineKeyboardButton(PAYMENT_METHODS[c]["label"], callback_data=f"pay_{c}")]
                      for c in PAYMENT_METHODS],
                    [InlineKeyboardButton("← Back", callback_data="choose_subscription")]
                ])
            )
        else:
            await q.edit_message_text("❌ Invalid plan selected.")



    elif data.startswith("pay_"):

        method = data.split("_", 1)[1]
        plan_type, plan_key = context.user_data.get("pending_plan", (None, None))

        if plan_type == "subscription":
            plan = SUBSCRIPTIONS.get(plan_key)
        elif plan_type == "pass":
            plan = REQUEST_PASS_OPTIONS.get(plan_key)
        else:
            await q.answer("❌ Plan not found.", show_alert=True)
            return

        try:
            username = q.from_user.username or str(q.from_user.id)
            order_id = f"{username}:{random.randint(100000,999999)}"
            invoice = NP_CLIENT.create_invoice({
                "price_amount": plan["price"],
                "price_currency": "usd",
                "pay_currency": method.lower(),
                "order_id": order_id,
                "ipn_callback_url": WEBHOOK_URL
            })
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"*💸 Invoice Created*\n\n"
                    f"Amount: `{invoice.price_amount} {invoice.price_currency}`\n"
                    f"[Pay Here]({invoice.invoice_url})\n\n"
                    "_You’ll be credited once payment is confirmed._"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            await q.edit_message_text(f"❌ Payment error: {e}")


    elif data == "back_to_main":
        plan = "Active" if has_active_subscription(user) else "None"
        balance = 0.00
        welcome_text = translations[lang]['welcome'].format(
            username=user, plan=plan, balance=f"{balance:.2f}"
        )
        keyboard = [
            [InlineKeyboardButton(translations[lang]['search_button'], callback_data="search"),
             InlineKeyboardButton(translations[lang]['shop_button'], callback_data="plans")],
            [InlineKeyboardButton(translations[lang]['profile_button'], callback_data="profile"),
             InlineKeyboardButton(translations[lang]['reviews_button'], callback_data="reviews")],
            [InlineKeyboardButton(translations[lang]['language_button'], callback_data="language")]
        ]
        await q.edit_message_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def handle_search(update: Update, context: CallbackContext):
    if await handle_broadcast(update, context):
        return
    user    = update.effective_user.username or str(update.effective_user.id)
    chat_id = update.effective_chat.id
    text    = update.message.text.strip()
    lang    = context.user_data.get("lang", "en")

    # Prevent multiple active searches per user
    if chat_id in search_in_progress:
        await update.message.reply_text("❌ Please wait until your current search finishes.")
        return

    # 1) Capturing the Query & launching the search immediately
    if context.user_data.get("awaiting_query"):
        # validate
        if len(text) < 2 or text.lower() in {tok.lower() for tok in BANNED_TOKENS}:
            return await update.message.reply_text(
                "❌ Query must be at least 2 characters and not a banned token."
            )

        # clear the flag
        context.user_data["awaiting_query"] = False
    if user not in ACCESS_USERS:
        if not has_active_subscription(user, SEARCH_COST):
            await update.message.reply_text(f"❌ You need at least ${SEARCH_COST} in balance. Use /topup to add.")
            return
        user_balances[user] = user_balances.get(user, 0.0) - SEARCH_COST

        # read query, format & size
        query  = text
        fmt    = context.user_data.get("result_format", "txt")
        max_mb = context.user_data.get("max_size_mb", MAX_UPLOAD // (1024*1024))

        if user not in ACCESS_USERS:
            if not has_active_subscription(user, SEARCH_COST):
                await update.message.reply_text(f"❌ You need at least ${SEARCH_COST} in balance. Use /topup to add.")
                return
            user_balances[user] = user_balances.get(user, 0.0) - SEARCH_COST
        # enqueue & notify
        pos = search_queue.qsize() + 1
        search_in_progress.add(chat_id)
        await search_queue.put((chat_id, query, None, user, fmt, max_mb))
        return

    # 2) Capturing the Max-Size (if you still want that submenu)
    if context.user_data.get("awaiting_size"):
        try:
            mb = int(text)
            if not (1 <= mb <= 19):
                raise ValueError
            context.user_data["awaiting_size"] = False
            context.user_data["max_size_mb"] = mb
            menu_text, menu_kb = get_search_menu(context, lang)
            await update.message.reply_text(
                f"✅ Max size set to *{mb} MB*\n\nReturning to Search menu:",
                parse_mode="Markdown",
                reply_markup=menu_kb
            )
        except ValueError:
            await update.message.reply_text("❌ Please send an integer between 1 and 19.")
        return

    # 3) Support /search command if they type it directly
    if text.startswith("/search"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return await update.message.reply_text("Usage: /search <query>")
        context.user_data["query"] = parts[1]

    # 4) Fallback: if we have a stored query (from /search), launch it too
    query = context.user_data.get("query")
    if query:
        fmt    = context.user_data.get("result_format", "txt")
        max_mb = context.user_data.get("max_size_mb", MAX_UPLOAD // (1024*1024))

        if user not in ACCESS_USERS:
            if not has_active_subscription(user, SEARCH_COST):
                await update.message.reply_text(f"❌ You need at least ${SEARCH_COST} in balance. Use /topup to add.")
                return
            user_balances[user] = user_balances.get(user, 0.0) - SEARCH_COST

        pos = search_queue.qsize() + 1
        await update.message.reply_text(
            f"🔎 Searching for `{query}` with .{fmt} up to {max_mb} MB…\n[{'░'*10}] 0% (Est. {pos*10}s)",
            parse_mode="Markdown"
        )
        search_in_progress.add(chat_id)
        await search_queue.put((chat_id, query, None, user, fmt, max_mb))

        # clear only the query (keep format & size if desired)
        context.user_data.pop("query", None)

    if len(query) < 2:
        await update.message.reply_text("❌ Query must be at least 2 characters.")
        return
    if query.lower() in {tok.lower() for tok in BANNED_TOKENS}:
        await update.message.reply_text("❌ Your query is not valid.")
        return

    context.user_data["awaiting_query"] = False
    if user not in ACCESS_USERS:
        if not has_active_subscription(user, SEARCH_COST):
            await update.message.reply_text(f"❌ You need at least ${SEARCH_COST} in balance. Use /topup to add.")
            return
        user_balances[user] = user_balances.get(user, 0.0) - SEARCH_COST
    await search_queue.put((
        update.effective_chat.id,
        query,
        context.user_data.get("prompt_id"),
        update.effective_user.username or str(update.effective_user.id)
    ))
    logger.info(f"Queued search `{query}`")

async def search_worker(app: Application):
    global search_queue
    while True:
        # 1) Unpack the next task (including format & max size)
        chat_id, query, prompt_id, user_label, fmt, max_mb = await search_queue.get()
        logger.info(f"🔎 Search requested by {user_label}: '{query}'  (fmt={fmt},  max_mb={max_mb})")

        # 2) Remove the “please send query” prompt if it’s still up
        if prompt_id:
            try:
                await app.bot.delete_message(chat_id=chat_id, message_id=prompt_id)
            except:
                pass

        # 3) Send “Searching…” status with a Stop button
        expected_time = 10
        status = await app.bot.send_message(
            chat_id=chat_id,
            text=f"🔎 Searching for `{query}`…\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Stop", callback_data="stop_search")]])
        )
        status_id = status.message_id

        # 4) Launch the external searcher subprocess
        try:
            proc = await asyncio.create_subprocess_exec(
                SEARCHER_BIN, "--index", TANTIVY_INDEX, "--query", query,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            running_search_process[chat_id] = proc
            start_time = time.time()
        except Exception as e:
            await app.bot.edit_message_text(
                chat_id=chat_id, message_id=status_id,
                text=f"❌ Failed to launch searcher: {e}"
            )
            search_in_progress.discard(chat_id)
            continue

        # 5) Stream its stdout into results.txt, updating status every second
        last_update = start_time
        with open("results.txt", "wb") as out:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                out.write(line)
                if time.time() - last_update >= 1:
                    elapsed = time.time() - start_time
                    percent = int((elapsed / expected_time) * 100)
                    if percent > 90:
                        percent = 90
                    bar = '▓' * (percent // 10) + '░' * (10 - percent // 10)
                    remaining = math.ceil(expected_time - elapsed) if elapsed < expected_time else 1
                    await app.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_id,
                        text=f"🔎 Searching for `{query}`…\n[{bar}] {percent}% (Est. {remaining}s)",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Stop", callback_data="stop_search")]])
                    )
                    last_update = time.time()

        await proc.wait()
        running_search_process.pop(chat_id, None)

        # 6) Handle Stop
        if chat_id in canceled_searches:
            canceled_searches.remove(chat_id)
            search_in_progress.discard(chat_id)
            try:
                await app.bot.edit_message_text(chat_id=chat_id, message_id=status_id, text="🛑 Search canceled.")
            except:
                pass
            await app.bot.send_message(
                chat_id=chat_id,
                text="🛑 Search canceled.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔎 Search Again", callback_data="search"),
                                                   InlineKeyboardButton("🏠 Home", callback_data="back_to_main")]])
            )
            continue

        # 7) Handle errors
        if proc.returncode != 0:
            err = (await proc.stderr.read()).decode().strip() or "Unknown error"

            await app.bot.edit_message_text(
                chat_id=chat_id, message_id=status_id,
                text=f"❌ Search failed: `{err}`", parse_mode="Markdown", reply_markup=None
            )
            search_in_progress.discard(chat_id)
            await app.bot.send_message(
                chat_id=chat_id,
                text="❌ Search failed.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔎 Search Again", callback_data="search"),
                                                   InlineKeyboardButton("🏠 Home", callback_data="back_to_main")]])
            )
            continue

        # 8) Count results
        line_count = sum(1 for _ in open("results.txt", "r", encoding="utf-8"))
        if line_count == 0:
            await app.bot.edit_message_text(
                chat_id=chat_id, message_id=status_id,
                text="⚠️ No results found.", reply_markup=None
            )
            search_in_progress.discard(chat_id)
            await app.bot.send_message(
                chat_id=chat_id,
                text="⚠️ No results found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔎 Search Again", callback_data="search"),
                                                   InlineKeyboardButton("🏠 Home", callback_data="back_to_main")]])
            )
            continue

        # 9) Demo‐users get blocked preview
        if user_label not in ACCESS_USERS:
            search_cooldowns[user_label] = time.time()
            await app.bot.edit_message_text(
                chat_id=chat_id, message_id=status_id,
                text=(
                    f"🔒 You found `{line_count}` lines for `{query}`.\n\n"
                    "💳 Subscribe to get full results.\n"
                    "❗ You’re on a 4-hour demo cooldown."
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 View Plans", callback_data="plans")]])
            )
            search_in_progress.discard(chat_id)
            await app.bot.send_message(
                chat_id=chat_id,
                text="✅ Search finished.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔎 Search Again", callback_data="search"),
                                                   InlineKeyboardButton("🏠 Home", callback_data="back_to_main")]])
            )
            continue

        # 10) Mark complete
        await app.bot.edit_message_text(
            chat_id=chat_id, message_id=status_id,
            text=f"✅ Search complete for `{query}`", parse_mode="Markdown", reply_markup=None
        )

        # 11) Split results.txt into parts up to max_mb
        size_bytes = os.path.getsize("results.txt")
        parts = []
        if size_bytes <= max_mb * 1024 * 1024:
            parts = ["results.txt"]
        else:
            cur, buf, idx = 0, [], 1
            with open("results.txt", "r", encoding="utf-8") as R:
                for line in R:
                    b = line.encode("utf-8")
                    if cur + len(b) > max_mb * 1024 * 1024 and buf:
                        fn = f"results_part{idx}.txt"
                        with open(fn, "w", encoding="utf-8") as O:
                            O.writelines(buf)
                        parts.append(fn)
                        buf, cur, idx = [], 0, idx + 1
                    buf.append(line)
                    cur += len(b)
                if buf:
                    fn = f"results_part{idx}.txt"
                    with open(fn, "w", encoding="utf-8") as O:
                        O.writelines(buf)
                    parts.append(fn)

        # 12) Send either an archive or the individual .txt parts
        if fmt in ("zip", "rar"):
            archive_name = f"results.{fmt}"
            if fmt == "zip":
                with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fn in parts:
                        zf.write(fn, arcname=os.path.basename(fn))
            else:
                try:
                    subprocess.run(["rar", "a", archive_name] + parts, check=True)
                except FileNotFoundError:
                    logger.warning("'rar' not found, using ZIP instead")
                    with zipfile.ZipFile(archive_name, "w", zipfile.ZIP_DEFLATED) as zf:
                        for fn in parts:
                            zf.write(fn, arcname=os.path.basename(fn))
            with open(archive_name, "rb") as af:
                await app.bot.send_document(chat_id=chat_id, document=af)
            # cleanup
            for fn in parts + [archive_name, "results.txt"]:
                try: os.remove(fn)
                except: pass
        else:
            for fn in parts:
                error_ids = []
                while True:
                    try:
                        with open(fn, "rb") as doc:
                            await app.bot.send_document(chat_id=chat_id, document=doc)
                        for mid in error_ids:
                            try: await app.bot.delete_message(chat_id=chat_id, message_id=mid)
                            except: pass
                        break
                    except Exception as se:
                        err_msg = await app.bot.send_message(chat_id=chat_id, text=f"❌ Failed to send {fn}: {se}")
                        error_ids.append(err_msg.message_id)
                        await asyncio.sleep(1)
            for fn in parts + ["results.txt"]:
                try: os.remove(fn)
                except: pass

        # 13) Offer “search again” if they’re subscribed
        await app.bot.send_message(
            chat_id=chat_id,
            text="✅ Search finished.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔎 Search Again", callback_data="search"),
                                               InlineKeyboardButton("🏠 Home", callback_data="back_to_main")]])
        )

        search_in_progress.discard(chat_id)

async def post_init(app: Application):
    global search_queue
    search_queue = asyncio.Queue()
    app.create_task(search_worker(app))

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addlist", addlist))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("topup", topup_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.run_polling()
    
if __name__ == "__main__":
    Thread(target=lambda: app_web.run(port=5000)).start()
    main()
