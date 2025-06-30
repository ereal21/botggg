from flask import request, jsonify
from . import config
import json
import requests

@config.app_web.route("/nowpayments-webhook", methods=["POST"])
def nowpayments_ipn():
    data = request.get_json()
    payment_id = str(data.get("payment_id"))
    order_id = data.get("order_id")
    status = data.get("payment_status")
    amount_usd = float(data.get("price_amount", 0))
    info = config.pending_invoices.pop(payment_id, None)
    username = order_id.split(":")[0] if order_id else (info["username"] if info else "")
    if status == "confirmed":
        config.user_balances[username] = config.user_balances.get(username, 0.0) + amount_usd
        if info:
            requests.post(f"{config.TELEGRAM_API}/deleteMessage", data={"chat_id": info['chat_id'], "message_id": info['message_id']})
            kb = json.dumps({'inline_keyboard': [[{'text': '🏠 Home', 'callback_data': 'back_to_main'}]]})
            requests.post(f"{config.TELEGRAM_API}/sendMessage", data={"chat_id": info['chat_id'], "text": f"✅ Your balance was topped up by ${amount_usd:.2f}", "reply_markup": kb})
    return jsonify({"status": "ok"})
