from fastapi import APIRouter, Depends

from typing import List
from app.schemas import UserShort

from app.database import users_collection
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

