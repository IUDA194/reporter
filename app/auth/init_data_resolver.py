import os
import hashlib
import hmac
import json
from urllib.parse import unquote

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

BOT_TOKEN = os.getenv("BOT_TOKEN")


def validate(hash_str, init_data, token, c_str="WebAppData"):
    """
    Validates the data received from the Telegram web app, using the
    method documented here: 
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app

    hash_str - the hash string passed by the webapp
    init_data - the query string passed by the webapp
    token - Telegram bot's token
    c_str - constant string (default = "WebAppData")
    """
    init_data = sorted([chunk.split("=") 
          for chunk in unquote(init_data).split("&") 
            if chunk[:len("hash=")]!="hash="],
        key=lambda x: x[0])
    init_data = "\n".join([f"{rec[0]}={rec[1]}" for rec in init_data])

    secret_key = hmac.new(c_str.encode(), token.encode(), hashlib.sha256).digest()
    data_check = hmac.new(secret_key, init_data.encode(), hashlib.sha256)
    return data_check.hexdigest() == hash_str

def verify_telegram_init_data(init_data: str, bot_token: str = BOT_TOKEN, c_str: str = "WebAppData") -> dict:
    """
    Проверяет подпись Telegram WebApp initData по актуальным рекомендациям Telegram.
    Возвращает dict всех параметров (user будет уже декодирован как объект).
    Использует validate() для проверки подписи.
    """
    params = [chunk.split("=", 1) for chunk in unquote(init_data).split("&") if chunk]
    hash_from_tg = None
    filtered_params = []
    for k, v in params:
        if k == "hash":
            hash_from_tg = v
        elif k != "signature":
            filtered_params.append((k, v))
    if not hash_from_tg:
        raise Exception("No hash in initData")
    
    # Проверяем подпись через validate
    if not validate(hash_from_tg, init_data, bot_token, c_str=c_str):
        raise Exception("Invalid signature in initData (validate)")

    # Если подпись валидна, продолжаем как раньше:
    filtered_params.sort(key=lambda x: x[0])
    out = dict(filtered_params)
    if "user" in out:
        try:
            out["user"] = json.loads(out["user"])
        except Exception:
            pass
    return out