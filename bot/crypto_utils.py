import requests

def get_crypto_amount(usd_amount, coin_id):
    response = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": coin_id, "vs_currencies": "usd"},
    )
    response.raise_for_status()
    price_data = response.json()
    crypto_price = price_data[coin_id]["usd"]
    return usd_amount / crypto_price
