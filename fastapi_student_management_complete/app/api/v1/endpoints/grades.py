from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_login, require_teacher
from app.core.database import get_db
from app.models.entities import Grade
from app.schemas.entities import GradeCreate, GradePageResponse, GradeResponse, GradeUpdate
from app.services.entity_service import create_with_log, delete_with_log, get_by_id, list_with_filters, update_with_log
from app.services.query_service import like

router = APIRouter(prefix="/grades", tags=["grades"])


@router.get("", response_model=GradePageResponse)
def list_grades(
    student_no: str | None = Query(default=None),
    student_name: str | None = Query(default=None),
    course_name: str | None = Query(default=None),
    score: float | None = Query(default=None),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    filters = [like(Grade.student_no, student_no), like(Grade.student_name, student_name), like(Grade.course_name, course_name)]
    if score is not None:
        filters.append(Grade.score == score)
    return list_with_filters(db, Grade, filters, sort_by, sort_order, page, page_size)


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(payload: GradeCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    return create_with_log(db, Grade, payload, user, "grades", "student_name")


@router.get("/{item_id}", response_model=GradeResponse)
def get_grade(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return get_by_id(db, Grade, item_id, "成绩记录不存在")


@router.put("/{item_id}", response_model=GradeResponse)
def update_grade(item_id: int, payload: GradeUpdate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, Grade, item_id, "成绩记录不存在")
    return update_with_log(db, obj, payload, user, "grades", "student_name")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, Grade, item_id, "成绩记录不存在")
    delete_with_log(db, obj, user, "grades", "student_name")
