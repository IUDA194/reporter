from pydantic import BaseModel, HttpUrl
from typing import List
from datetime import date, datetime

class TaskInput(BaseModel):
    url: HttpUrl
    description: str

class TaskSuccessResponse(BaseModel):
    date: date
    developer: str
    yesterday: List[TaskInput]
    today: List[TaskInput]
    blockers: List[TaskInput]
