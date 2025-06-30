import random
import asyncio
import io
import qrcode
from telegram.ext import CallbackContext
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from . import config

async def expire_invoice(payment_id: str):
    await asyncio.sleep(1800)
    info = config.pending_invoices.pop(payment_id, None)
    if info and config.telegram_app:
        try:
            await config.telegram_app.bot.delete_message(chat_id=info['chat_id'], message_id=info['message_id'])
        except Exception:
            pass
        await config.telegram_app.bot.send_message(
            chat_id=info['chat_id'],
            text='⏰ Invoice expired.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🏠 Home', callback_data='back_to_main')]])
        )

async def topup_cmd(update: Update, context: CallbackContext):
    if not context.args:
        return await update.message.reply_text("Usage: /topup <amount>")
    try:
        amount = float(context.args[0])
    except ValueError:
        return await update.message.reply_text("Invalid amount.")
    username = update.effective_user.username or str(update.effective_user.id)
    chat_id = update.effective_chat.id
    order_id = f"{username}:{chat_id}:{random.randint(100000,999999)}"
    payment = config.NP_CLIENT.create_payment(
        price_amount=amount,
        price_currency="usd",
        pay_currency="btc",
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
    kb = InlineKeyboardMarkup([[InlineKeyboardButton('🏠 Home', callback_data='back_to_main')]])
    msg = await update.message.reply_photo(photo=bio, caption=caption, parse_mode='Markdown', reply_markup=kb)
    payment_id = str(payment['payment_id'])
    config.pending_invoices[payment_id] = {
        'chat_id': chat_id,
        'message_id': msg.message_id,
        'username': username,
        'amount': amount,
    }
    context.application.create_task(expire_invoice(payment_id))
