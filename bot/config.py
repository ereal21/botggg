import os
import asyncio
import logging
from flask import Flask
import nowpayments
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Payment client and webhook URL
from nowpayments import NOWPayments
NP_CLIENT = NOWPayments(os.getenv("NOWPAYMENTS_API_KEY", ""))
WEBHOOK_URL = os.getenv("NGROK_URL", "") + "/nowpayments-webhook"
app_web = Flask(__name__)

# Core configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEARCHER_BIN = os.getenv(
    "SEARCHER_BIN",
    r"B:\\Indexing\\tantivy_searcher\\tantivy_searcher\\target\\release\\tantivy_searcher.exe",
)
TANTIVY_INDEX = os.getenv("TANTIVY_INDEX", r"Z:\\as")

ACCESS_USERS = {"Inereal", "Penguinite", "KN0O7", "CoreyD6", "Kqizen"}
ADMIN_USERS = {"Inereal"}

BANNED_TOKENS = [
    "www.", "https://", "http://", ".com", "com", "org", ".org", ".www", "://", "/", ":"
]

MAX_UPLOAD = 19 * 1024 * 1024
SEARCH_COST = 1.0

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
    "TRX": "tron", "SOL": "solana", "BTC": "bitcoin", "ETH": "ethereum", "XRP": "ripple",
    "TRXUSDT": "tether", "BNB": "binancecoin", "LTC": "litecoin", "USDC_SOL": "usd-coin",
    "USDC_ETH": "usd-coin", "TON": "the-open-network", "BCH": "bitcoin-cash",
    "ETC": "ethereum-classic", "XMR": "monero"
}


def get_welcome_text(lang: str, username: str, plan: str, balance: str) -> str:
    """Return the formatted welcome text for the user."""
    template = translations.get(lang, translations['en'])['welcome']
    if isinstance(template, (tuple, list)):
        template = ''.join(template)
    return template.format(username=username, plan=plan, balance=balance)

translations = {
    'en': {
        'welcome': (
            "👋 Welcome, @{username}!\n💰 Balance: {balance} EUR\n📝Plan: {plan}\n\n",
            "⚠️ Note: No refunds.\n💳 If the transacted amount is less than the required amount, the payment will not be confirmed. Please ensure you send the exact amount. Verify that your exchange provider does not deduct any sending fees. If you are unsure, it is advisable to send a slightly higher amount.\n\n",
            "_Experience the difference!_",
        ),
        'profile': "🎉 Your Profile\n\n👤 Plan: {plan}\n💰 Balance: {balance} EUR",
        'search_button': "🔎 Search",
        'shop_button': "🪙 Top Up",
        'profile_button': "👤 Profile",
        'reviews_button': "⭐ Reviews",
        'language_button': "🌐 Language",
        'language_prompt': "🌐 Choose your language:",
        'plans_menu': "💳 *Plans*\nChoose an option:",
        'choose_subscription': "*Choose subscription plan:*",
        'choose_search_pass': "*Choose request pass:*",
        'waiting_confirmation': "⏳ *Waiting for payment confirmation...*\nPlease transfer the funds within 30 minutes.",
        'choose_payment_method': "*Choose payment method:*",
    },
    'es': {
        'welcome': (
            "👋 Bienvenido, @{username}!\n💰 Saldo: {balance} EUR\nPlan: {plan}\n\n",
            "⚠️ Nota: No hay reembolsos.\n💳 Si la cantidad transferida es menor que la requerida, el pago no será confirmado. Asegúrate de enviar la cantidad exacta. Verifica que tu proveedor de cambio no deduzca ninguna tarifa al enviar. Si no estás seguro, es recomendable enviar una cantidad ligeramente mayor.\n\n",
            "_¡Vive la diferencia!_",
        ),
        'profile': "🎉 Tu perfil\n\n👤 Plan: {plan}\n💰 Saldo: {balance} EUR",
        'search_button': "🔎 Buscar",
        'shop_button': "🪙 Recargar",
        'profile_button': "👤 Perfil",
        'reviews_button': "⭐ Reseñas",
        'language_button': "🌐 Idioma",
        'language_prompt': "🌐 Elige tu idioma:",
        'plans_menu': "💳 *Planes*\nElige una opción:",
        'choose_subscription': "*Elige un plan de suscripción:*",
        'choose_search_pass': "*Elige un pase de búsqueda:*",
        'waiting_confirmation': "⏳ *Esperando la confirmación del pago...*\nPor favor, transfiera los fondos dentro de 30 minutos.",
        'choose_payment_method': "*Elige el método de pago:*",
    },
    'pt': {
        'welcome': (
            "👋 Bem-vindo, @{username}!\n💰 Saldo: {balance} EUR\nPlano: {plan}\n\n",
            "⚠️ Atenção: Sem reembolsos.\n💳 Se o valor transacionado for menor do que o valor exigido, o pagamento não será confirmado. Por favor, envie o valor exato. Verifique se seu provedor de câmbio não deduz nenhuma taxa de envio. Se não tiver certeza, é aconselhável enviar um valor ligeiramente maior.\n\n",
            "_Sinta a diferença!_",
        ),
        'profile': "🎉 Seu perfil\n\n👤 Plano: {plan}\n💰 Saldo: {balance} EUR",
        'search_button': "🔎 Buscar",
        'shop_button': "🪙 Recarregar",
        'profile_button': "👤 Perfil",
        'reviews_button': "⭐ Avaliações",
        'language_button': "🌐 Idioma",
        'language_prompt': "🌐 Escolha seu idioma:",
        'plans_menu': "💳 *Planos*\nEscolha uma opção:",
        'choose_subscription': "*Escolha um plano de assinatura:*",
        'choose_search_pass': "*Escolha um passe de pesquisa:*",
        'waiting_confirmation': "⏳ *Aguardando confirmação de pagamento...*\nPor favor, transfira os fundos dentro de 30 minutos.",
        'choose_payment_method': "*Escolha o método de pagamento:*",
    },
    'ru': {
        'welcome': (
            "👋 Добро пожаловать, @{username}!\n💰 Баланс: {balance} EUR\nПлан: {plan}\n\n",
            "⚠️ Внимание: возврата средств не предусмотрено.\n💳 Если переведенная сумма меньше требуемой, платеж не будет подтвержден. Пожалуйста, отправьте точную сумму. Проверьте, не удерживает ли ваш обменник комиссию при отправке. Если вы не уверены, рекомендуется отправить немного больше.\n\n",
            "_Ощутите разницу!_",
        ),
        'profile': "🎉 Ваш профиль\n\n👤 План: {plan}\n💰 Баланс: {balance} EUR",
        'search_button': "🔎 Поиск",
        'shop_button': "🪙 Пополнить",
        'profile_button': "👤 Профиль",
        'reviews_button': "⭐ Отзывы",
        'language_button': "🌐 Язык",
        'language_prompt': "🌐 Выберите язык:",
        'plans_menu': "💳 *Тарифы*\nВыберите опцию:",
        'choose_subscription': "*Выберите план подписки:*",
        'choose_search_pass': "*Выберите пропуск для поиска:*",
        'waiting_confirmation': "⏳ *Ожидание подтверждения оплаты...*\nПожалуйста, переведите средства в течение 30 минут.",
        'choose_payment_method': "*Выберите способ оплаты:*",
    },
    'zh': {
        'welcome': (
            "👋 欢迎, @{username}!\n💰 余额: {balance} EUR\n计划: {plan}\n\n",
            "⚠️ 注意: 不予退款。\n💳 如果交易金额少于所需金额，支付将无法确认。请确保您发送准确的金额。请确认您的兑换服务提供商不会扣除任何发送费用。如果不确定，建议多发送一些金额。\n\n",
            "_体验不同！_",
        ),
        'profile': "🎉 您的个人资料\n\n👤 计划: {plan}\n💰 余额: {balance} EUR",
        'search_button': "🔎 搜索",
        'shop_button': "🪙 充值",
        'profile_button': "👤 个人资料",
        'reviews_button': "⭐ 评论",
        'language_button': "🌐 语言",
        'language_prompt': "🌐 选择您的语言:",
        'plans_menu': "💳 *计划*\n选择一个选项:",
        'choose_subscription': "*选择订阅计划:*",
        'choose_search_pass': "*选择搜索通行证:*",
        'waiting_confirmation': "⏳ *等待付款确认...*\n请在30分钟内转账。",
        'choose_payment_method': "*选择付款方式:*",
    }
}

# Runtime state
search_queue: asyncio.Queue | None = None
search_in_progress = set()
running_search_process = {}
canceled_searches = set()
search_cooldowns = {}
user_subscriptions = {}
COOLDOWN_HOURS = 4
user_balances = {}
pending_invoices = {}
telegram_app = None
