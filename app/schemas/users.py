from pydantic import BaseModel, Field

class UserShort(BaseModel):
    user_id: str = Field(..., description="ID пользователя в базе данных (ObjectId)")
    full_name: str = Field(..., description="Полное имя пользователя")
