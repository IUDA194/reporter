import os

JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")
JWT_ALGORITHM = "HS256"
BOT_URL = os.getenv("BOT_URL", "https://t.me/testikkkkki8_bot")