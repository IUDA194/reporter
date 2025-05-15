from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Any
from datetime import datetime

class TaskInput(BaseModel):
    url: HttpUrl
    description: str

class TaskSuccessResponse(BaseModel):
    date: datetime
    developer: str
    yesterday: List[TaskInput]
    today: List[TaskInput]
    blockers: List[TaskInput]

class ReportUpdate(BaseModel):
    date: Optional[datetime] = None
    developer: Optional[str] = None
    yesterday: Optional[List[TaskInput]] = None
    today: Optional[List[TaskInput]] = None
    blockers: Optional[List[TaskInput]] = None


class ReportOut(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    date: datetime
    developer: str
    yesterday: List[Any]
    today: List[Any]
    blockers: List[Any]
    created_at: datetime

    class Config:
        allow_population_by_field_name = True
