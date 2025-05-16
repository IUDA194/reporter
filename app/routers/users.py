from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from typing import List
from app.schemas import UserShort, UserProfile

from app.database import users_collection, collection
from app.auth import get_user_from_jwt

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
