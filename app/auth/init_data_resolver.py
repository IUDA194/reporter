import os
import hashlib
import hmac
import urllib.parse

from fastapi import HTTPException

BOT_TOKEN = os.getenv("BOT_TOKEN")

def verify_telegram_init_data(init_data: str, bot_token: str = BOT_TOKEN) -> dict:
    """
    Проверяет подпись Telegram initData и возвращает словарь с user-данными.
    """
    params = dict(urllib.parse.parse_qsl(init_data.replace('?', '')))
    hash_from_tg = params.pop('hash', None)
    if not hash_from_tg:
        raise HTTPException(status_code=400, detail="No hash in initData")
    
    data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(params.items())])
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if calculated_hash != hash_from_tg:
        raise HTTPException(status_code=401, detail="Invalid signature in initData")
    return params
