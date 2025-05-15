from pydantic import BaseModel, Field
from typing import Optional

class UserShort(BaseModel):
    user_id: str = Field(..., description="ID пользователя в базе данных (ObjectId)")
    full_name: str = Field(..., description="Полное имя пользователя")

class UserProfile(BaseModel):
    user_id: str
    full_name: str
    developer_name: Optional[str] = None