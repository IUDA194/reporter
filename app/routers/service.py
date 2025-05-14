import os
import jwt
import json
import random
import uuid

from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.database import users_collection
from app.routers.sockets import active_connections
from app.auth import JWT_ALGORITHM, JWT_SECRET

router = APIRouter()

@router.post("/confirm-code", include_in_schema=False)
async def confirm_code(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    uuid_field = data.get("uuid")
    chat_id = data.get("chat_id")
    username = data.get("username")
    full_name = data.get("full_name")
    referred_by = data.get("referred_by")

    if not uuid_field or not chat_id:
        return JSONResponse({"error": "uuid and chat_id are required"}, status_code=400)

    websocket = active_connections.get(uuid_field)
    if not websocket:
        return JSONResponse({"error": "WebSocket not found or expired"}, status_code=404)

    user = await users_collection.find_one({"chat_id": str(chat_id)})
    if not user:
        user_data = {
            "chat_id": str(chat_id),
            "username": username,
            "full_name": full_name,
            "referred_by": referred_by,
            "created_at": datetime.utcnow()
        }
        insert_result = await users_collection.insert_one(user_data)
        user_id = insert_result.inserted_id
    else:
        user_id = user["_id"]

    payload = {
        "user_id": str(user_id),
        "chat_id": chat_id,
        "username": username,
        "full_name": full_name,
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    message = {
        "status": "success",
        "access_token": jwt_token,
    }

    await websocket.send_text(json.dumps(message))
    return JSONResponse({"status": "sent", "token": jwt_token})

@router.get(
    "/test-token",
    summary="Генерирует случайный JWT-токен и сохраняет/находит пользователя в БД",
    include_in_schema=False
)
async def get_test_token():
    """
    Автоматически генерирует:
    - chat_id (int)
    - username (str)
    - full_name (str)
    - referred_by (int или None)
    Сохраняет пользователя в users_collection (если ещё не был).
    Возвращает JWT с полями user_id, chat_id, username, full_name, iat.
    """
    if not os.getenv("DEBUG", "False").lower() in ("true", "1"):
        raise HTTPException(status_code=403, detail="Not allowed in production")
        
    chat_id = random.randint(100_000, 999_999)
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    full_name = f"User {username}"
    referred_by = random.choice([None, random.randint(100_000, 999_999)])

    chat_id_str = str(chat_id)

    user = await users_collection.find_one({"chat_id": chat_id_str})
    if not user:
        user_data = {
            "chat_id": chat_id_str,
            "username": username,
            "full_name": full_name,
            "referred_by": referred_by,
            "created_at": datetime.utcnow()
        }
        insert_result = await users_collection.insert_one(user_data)
        user_id = insert_result.inserted_id
    else:
        user_id = user["_id"]

    payload = {
        "user_id": str(user_id),   # берём реальный _id из Mongo
        "chat_id": chat_id,
        "username": username,
        "full_name": full_name,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token}

@router.delete(
    "/delete-test-users",
    summary="Удаляет всех тестовых пользователей (username начинается с testuser_)",
    include_in_schema=False
)
async def delete_test_users():
    if not os.getenv("DEBUG", "False").lower() in ("true", "1"):
        raise HTTPException(status_code=403, detail="Not allowed in production")
    
    result = await users_collection.delete_many({
        "username": {"$regex": "^testuser_"}
    })
    return JSONResponse(
        content={
            "status": "success",
            "deleted_count": result.deleted_count
        },
        status_code=200
    )
