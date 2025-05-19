from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserShort(BaseModel):
    user_id: str = Field(..., description="ID пользователя в базе данных (ObjectId)")
    full_name: str = Field(..., description="Полное имя пользователя")

class UserProfile(BaseModel):
    user_id: str = Field(..., description="ID пользователя в базе данных (ObjectId)")
    full_name: str = Field(..., description="Полное имя пользователя")
    developer_name: Optional[str] = Field(None, description="Имя последнего разработчика, связанного с пользователем")

class AuthRequest(BaseModel):
    initData: str = Field(..., description="Строка initData, которую передает Telegram Mini App")

class UserAuthOut(BaseModel):
    user_id: str = Field(..., description="ID пользователя в базе данных (ObjectId)")
    chat_id: int = Field(..., description="Telegram chat_id пользователя")
    username: Optional[str] = Field(None, description="Username пользователя в Telegram")
    full_name: Optional[str] = Field(None, description="Полное имя пользователя")
    iat: datetime = Field(..., description="Дата и время выдачи токена (issued at)")
    exp: datetime = Field(..., description="Дата и время истечения токена (expires at)")

class AuthResponse(BaseModel):
    access_token: str = Field(..., description="JWT-токен для дальнейших запросов к API")
    user: UserAuthOut = Field(..., description="Данные пользователя, для которого выдан токен")
