import os

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:1213@127.0.0.1:27019/admin")

client = AsyncIOMotorClient(MONGO_URI)
db = client["test_db"]
collection = db["task_reports"]
users_collection = db["users"]