from fastapi import APIRouter, Query, HTTPException, Depends, status, Path
from typing import Optional, List
from datetime import date, datetime
from bson import ObjectId

from app.schemas import TaskSuccessResponse, ReportOut, ReportUpdate
from app.database import collection
from app.auth import get_user_from_jwt
from app.utils.enrich_task import enrich_task


router = APIRouter()

@router.post(
    "/submit",
    status_code=status.HTTP_201_CREATED,
    response_description="Отчет успешно сохранен",
    summary="Отправка ежедневного отчета",
    response_model=dict,
    tags=["Reports"],
)
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

@router.get(
    "/reports",
    response_model=None,
    summary="Получение отчетов",
    tags=["Reports"],
    description="""
    Возвращает список всех отчётов, либо только отчёты указанного пользователя, если задан `owner_id`.

    - **date** (опционально): дата отчета `YYYY-MM-DD`
    - **owner_id** (опционально): ID пользователя (для фильтрации)
    """
)
async def get_reports(
    date: Optional[date] = Query(None, description="Дата отчёта в формате YYYY-MM-DD"),
    owner_id: Optional[str] = Query(None, description="ID пользователя для фильтрации отчётов"),
    user_payload: dict = Depends(get_user_from_jwt)
):
    query = {"is_deleted": {"$ne": True}}

    if owner_id:
        try:
            query["user_id"] = ObjectId(owner_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid owner_id format")

    if date:
        query["date"] = date.isoformat()

    cursor = collection.find(query)
    reports = await cursor.to_list(length=None)

    for report in reports:
        report["_id"] = str(report["_id"])
        if "user_id" in report:
            report["user_id"] = str(report["user_id"])
        if "created_at" in report and hasattr(report["created_at"], "isoformat"):
            report["created_at"] = report["created_at"].isoformat()

    return reports

@router.get(
    "/reports/{report_id}",
    response_model=ReportOut,
    summary="Получение одного отчёта по ID",
    tags=["Reports"],
)
async def get_report(
    report_id: str = Path(..., description="ID отчёта"),
    user_payload: dict = Depends(get_user_from_jwt),
):
    try:
        oid = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    user_id = user_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")

    report = await collection.find_one({"_id": oid, "user_id": ObjectId(user_id), "is_deleted": {"$ne": True}})
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report["_id"] = str(report["_id"])
    report["user_id"] = str(report["user_id"])
    if isinstance(report.get("created_at"), datetime):
        report["created_at"] = report["created_at"]

    return report


@router.patch(
    "/reports/{report_id}",
    response_model=ReportOut,
    summary="Частичное обновление отчёта",
    tags=["Reports"],
)
async def update_report(
    report_id: str = Path(..., description="ID отчёта"),
    data: ReportUpdate = None,
    user_payload: dict = Depends(get_user_from_jwt),
):
    try:
        oid = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    user_id = user_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")

    update_fields = {}
    if data.date is not None:
        update_fields["date"] = data.date.isoformat()
    if data.developer is not None:
        update_fields["developer"] = data.developer
    if data.yesterday is not None:
        update_fields["yesterday"] = [enrich_task(t) for t in data.yesterday]
    if data.today is not None:
        update_fields["today"] = [enrich_task(t) for t in data.today]
    if data.blockers is not None:
        update_fields["blockers"] = [enrich_task(t) for t in data.blockers]

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    update_fields["updated_at"] = datetime.utcnow().isoformat()

    result = await collection.update_one(
        {"_id": oid, "user_id": ObjectId(user_id)},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Report not found or no access")

    report = await collection.find_one({"_id": oid})
    report["_id"] = str(report["_id"])
    report["user_id"] = str(report["user_id"])
    if isinstance(report.get("created_at"), datetime):
        report["created_at"] = report["created_at"]
    return report

@router.delete(
    "/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление отчёта",
    tags=["Reports"],
    description="Удаляет отчёт по ID. Доступно только владельцу."
)
async def delete_report(
    report_id: str = Path(..., description="ID отчёта"),
    user_payload: dict = Depends(get_user_from_jwt),
):
    try:
        oid = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    user_id = user_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")

    result = await collection.update_one(
        {"_id": oid, "user_id": ObjectId(user_id)},
        {"$set": {"is_deleted": True, "deleted_at": datetime.utcnow().isoformat()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Report not found or no access")
