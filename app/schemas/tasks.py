from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Any
from datetime import date, datetime
from datetime import date as date_film

class TaskInput(BaseModel):
    url: HttpUrl
    description: str

class TaskSuccessResponse(BaseModel):
    date: date
    developer: str
    yesterday: List[TaskInput]
    today: List[TaskInput]
    blockers: List[TaskInput]

class ReportUpdate(BaseModel):
    date: Optional[date_film] = None
    developer: Optional[str] = None
    yesterday: Optional[List[TaskInput]] = None
    today: Optional[List[TaskInput]] = None
    blockers: Optional[List[TaskInput]] = None


class ReportOut(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    date: date
    developer: str
    yesterday: List[Any]
    today: List[Any]
    blockers: List[Any]
    created_at: datetime

    class Config:
        allow_population_by_field_name = True
