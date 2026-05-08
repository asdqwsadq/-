from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.schemas.entities import OperationLogPageResponse
from app.services.log_service import list_logs_service

router = APIRouter(tags=["logs"])


@router.get("/logs", response_model=OperationLogPageResponse)
def list_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_admin),
):
    return list_logs_service(db, page=page, page_size=page_size)
