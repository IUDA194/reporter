from fastapi import APIRouter

from typing import List
from app.schemas import UserShort

from app.database import users_collection

router = APIRouter()

@router.get(
    "/users",
    response_model=List[UserShort],
    summary="Получить список всех пользователей"
)
async def get_all_users():
    users_cursor = users_collection.find({}, {"full_name": 1})
    users = []
    async for user in users_cursor:
        users.append(UserShort(
            user_id=str(user["_id"]),
            full_name=user.get("full_name", "")
        ))
    return users

