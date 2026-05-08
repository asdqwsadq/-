from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_login
from app.core.database import get_db
from app.services.dashboard_service import get_dashboard_stats, get_grade_statistics

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard-stats")
def dashboard_stats(db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return get_dashboard_stats(db)


@router.get("/grades/statistics")
def grade_statistics(db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return get_grade_statistics(db)


@router.get("/grade-statistics")
def grade_stats_alias(db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return get_grade_statistics(db)
