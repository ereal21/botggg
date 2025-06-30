from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram import Update
from . import config
from .menu import get_search_menu
from .subscriptions import has_active_subscription
from .topup import expire_invoice
import random
import io
import asyncio
import qrcode
import requests

async def button_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    data = q.data
    user = update.effective_user.username or ""
    chat_id = q.message.chat.id
    lang = context.user_data.get("lang", "en")

    if data == "stop_search":
        proc = config.running_search_process.get(chat_id)
        if proc:
            proc.kill()
            config.canceled_searches.add(chat_id)
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
            [InlineKeyboardButton("← Back", callback_data="search")],
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
        await q.edit_message_text("📥 Send the max file size in MB (1-19):", reply_markup=kb)
        return

    if data == "topup":
        context.user_data["awaiting_topup_amount"] = True
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="back_to_main")]])
        await q.edit_message_text("💰 Enter the amount in USD you want to top up:", reply_markup=kb)
        return

    if data.startswith("topup_method_"):
        method = data.split("_", 2)[2]
        amount = context.user_data.get("topup_amount")
        if not amount:
            await q.answer("No amount set", show_alert=True)
            return
        username = q.from_user.username or str(q.from_user.id)
        order_id = f"{username}:{chat_id}:{random.randint(100000,999999)}"
        try:
            payment = config.NP_CLIENT.create_payment(
                price_amount=amount,
                price_currency="usd",
                pay_currency=method,
                order_id=order_id,
                ipn_callback_url=config.WEBHOOK_URL,
            )
            qr = qrcode.make(payment.get("invoice_url", ""))
            bio = io.BytesIO()
            qr.save(bio, format="PNG")
            bio.seek(0)
            caption = (
                f"*Send {payment['pay_amount']} {payment['pay_currency']}*\n"
                f"`{payment['pay_address']}`\n"
                f"[Pay Page]({payment['invoice_url']})\n"
                "_Expires in 30 minutes_"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="back_to_main")]])
            msg = await q.message.reply_photo(photo=bio, caption=caption, parse_mode="Markdown", reply_markup=kb)
            payment_id = str(payment['payment_id'])
            config.pending_invoices[payment_id] = {
                "chat_id": chat_id,
                "message_id": msg.message_id,
                "username": username,
                "amount": amount,
            }
            context.application.create_task(expire_invoice(payment_id))
        except Exception as e:
            await q.edit_message_text(f"❌ Payment error: {e}")
        return

    if data.startswith("pay_"):
        method = data.split("_", 1)[1]
        plan_type, plan_key = context.user_data.get("pending_plan", (None, None))
        if plan_type == "subscription":
            plan = config.SUBSCRIPTIONS.get(plan_key)
        elif plan_type == "pass":
            plan = config.REQUEST_PASS_OPTIONS.get(plan_key)
        else:
            await q.answer("❌ Plan not found.", show_alert=True)
            return
        try:
            username = q.from_user.username or str(q.from_user.id)
            order_id = f"{username}:{random.randint(100000,999999)}"
            invoice = config.NP_CLIENT.create_payment(
                price_amount=plan["price"],
                price_currency="usd",
                pay_currency=method.lower(),
                order_id=order_id,
                ipn_callback_url=config.WEBHOOK_URL,
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"*💸 Invoice Created*\n\n"
                    f"Amount: `{invoice['price_amount']} {invoice['price_currency']}`\n"
                    f"[Pay Here]({invoice['invoice_url']})\n\n"
                    "_You’ll be credited once payment is confirmed._",
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            await q.edit_message_text(f"❌ Payment error: {e}")
        return


    if data == "back_to_main":
        plan = "Active" if has_active_subscription(user) else "None"
        balance = config.user_balances.get(user, 0.0)

        welcome_text = config.get_welcome_text(
            lang,
            username=user,
            plan=plan,
            balance=f"{balance:.2f}",

        welcome_text = config.translations[lang]['welcome'].format(
            username=user, plan=plan, balance=f"{balance:.2f}"

        )
        keyboard = [
            [InlineKeyboardButton(config.translations[lang]['search_button'], callback_data="search"),
             InlineKeyboardButton(config.translations[lang]['shop_button'], callback_data="topup")],
            [InlineKeyboardButton(config.translations[lang]['profile_button'], callback_data="profile"),
             InlineKeyboardButton(config.translations[lang]['reviews_button'], callback_data="reviews")],
            [InlineKeyboardButton(config.translations[lang]['language_button'], callback_data="language")]
        ]
        await q.edit_message_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )



