import jwt
import json

from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.database import users_collection
from app.routers.sockets import active_connections
from app.auth import JWT_ALGORITHM, JWT_SECRET

router = APIRouter()

@router.post("/confirm-code")
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
