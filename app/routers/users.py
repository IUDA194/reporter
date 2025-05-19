import jwt

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from bson import ObjectId

from typing import List
from datetime import datetime, timedelta

from app.schemas import UserShort, UserProfile, AuthResponse
from app.database import users_collection, collection
from app.auth import get_user_from_jwt, verify_telegram_init_data, JWT_ALGORITHM, JWT_SECRET

router = APIRouter()

@router.get(
    "/users",
    response_model=List[UserShort],
    summary="Получить список всех пользователей",
    tags=["Users"],
)
async def get_all_users(user_payload: dict = Depends(get_user_from_jwt)):
    users_cursor = users_collection.find({}, {"full_name": 1})
    users = []
    async for user in users_cursor:
        users.append(UserShort(
            user_id=str(user["_id"]),
            full_name=user.get("full_name", "")
        ))
    return users

@router.get(
    "/profile",
    response_model=UserProfile,
    summary="Профиль текущего пользователя",
    tags=["Users"],
)
async def get_my_profile(user_payload: dict = Depends(get_user_from_jwt)):
    user_id = user_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")

    oid = ObjectId(user_id)

    user = await users_collection.find_one({"_id": oid}, {"full_name": 1})
    full_name = user.get("full_name", "") if user else ""

    latest_report = await collection.find_one(
        {"user_id": oid, "is_deleted": {"$ne": True}, "developer": {"$exists": True, "$ne": ""}},
        sort=[("created_at", -1)]
    )
    if latest_report: developer_name = latest_report.get("developer") if latest_report.get("developer") else None
    else: developer_name = None

    return UserProfile(
        user_id=str(oid),
        full_name=full_name,
        developer_name=developer_name
    )

@router.post(
    "/auth",
    response_model=AuthResponse,
    summary="Авторизация через Telegram Mini App",
    tags=["Auth"],
    description=(
        "Авторизация пользователя через Telegram Mini App.<br><br>"
        "Передайте строку <code>initData</code> из Telegram WebApp.<br>"
        "Сервер проверит подпись, создаст или найдёт пользователя и вернёт JWT-токен.<br><br>"
        "<b>Пример запроса:</b><br>"
        "<pre>{\n  \"initData\": \"user=...&hash=...\"\n}</pre>"
        "<b>Пример успешного ответа:</b><br>"
        "<pre>{\n"
        "  \"access_token\": \"eyJhbGciOi...\",\n"
        "  \"user\": {\n"
        "    \"user_id\": \"6631b3c1d2f4...\",\n"
        "    \"chat_id\": 12345678,\n"
        "    \"username\": \"nickname\",\n"
        "    \"full_name\": \"John Doe\",\n"
        "    \"iat\": \"2024-05-19T13:32:00.123456\",\n"
        "    \"exp\": \"2024-05-21T13:32:00.123456\"\n"
        "  }\n"
        "}</pre>"
    )
)
async def auth_by_tma(request: Request):
    """
    Принимает Telegram initData, проверяет подпись и выдает JWT-токен.
    """
    body = await request.json()
    init_data = body.get("initData")
    if not init_data:
        return JSONResponse({"error": "initData required"}, status_code=400)

    try:
        tg_user = verify_telegram_init_data(init_data)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=e.status_code)

    chat_id = tg_user.get("user", None)
    if isinstance(chat_id, dict):
        chat_id = chat_id.get("id")
    if not chat_id:
        chat_id = tg_user.get("id") or tg_user.get("user_id")
    username = tg_user.get("username")
    full_name = tg_user.get("first_name", "")
    if tg_user.get("last_name"):
        full_name += " " + tg_user.get("last_name")

    user = await users_collection.find_one({"chat_id": str(chat_id)})
    if not user:
        user_data = {
            "chat_id": str(chat_id),
            "username": username,
            "full_name": full_name,
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
        "iat": datetime.utcnow().isoformat(),
        "exp": (datetime.utcnow() + timedelta(days=2)).isoformat(),
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return JSONResponse({"access_token": jwt_token, "user": payload})