from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Request, Header, HTTPException, Depends
from typing import Optional
from datetime import date, datetime
from bson import ObjectId
import os
import json
import uuid
import jwt

from app.schemas import TaskInput, TaskSuccessResponse
from app.database import collection, redis, users_collection
from app.auth import JWT_ALGORITHM, JWT_SECRET, BOT_URL, get_user_from_jwt
from app.utils import enrich_task


router = APIRouter()

@router.post("/submit")
async def submit(data: TaskSuccessResponse, user_payload: dict = Depends(get_user_from_jwt)):
    user_id = user_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")

    enriched_data = {
        "user_id": ObjectId(user_id),
        "date": data.date.isoformat(),
        "developer": data.developer,
        "yesterday": [enrich_task(task) for task in data.yesterday],
        "today": [enrich_task(task) for task in data.today],
        "blockers": [enrich_task(task) for task in data.blockers],
        "created_at": datetime.utcnow().isoformat()
    }
    result = await collection.insert_one(enriched_data)
    return {"inserted_id": str(result.inserted_id)}

@router.get("/reports")
async def get_reports(
    date: Optional[date] = Query(None, description="Дата отчёта в формате YYYY-MM-DD"),
    owner_id: Optional[str] = Query(None, description="ID пользователя, если нужно посмотреть чужие отчёты"),
    user_payload: dict = Depends(get_user_from_jwt)
):
    if owner_id:
        try:
            query_user_id = ObjectId(owner_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid owner_id format")
    else:
        user_id = user_payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        query_user_id = ObjectId(user_id)

    query = {"user_id": query_user_id}
    if date:
        query["date"] = date.isoformat()

    cursor = collection.find(query)
    reports = await cursor.to_list(length=None)
    for report in reports:
        report["_id"] = str(report["_id"])
        report["user_id"] = str(report["user_id"])
        if "created_at" in report and isinstance(report["created_at"], datetime):
            report["created_at"] = report["created_at"].isoformat()
    return reports