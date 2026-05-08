from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_login, require_teacher
from app.core.database import get_db
from app.models.entities import Employment
from app.schemas.entities import EmploymentCreate, EmploymentPageResponse, EmploymentResponse, EmploymentUpdate
from app.services.entity_service import create_with_log, delete_with_log, get_by_id, list_with_filters, update_with_log
from app.services.query_service import like

router = APIRouter(prefix="/employments", tags=["employments"])


@router.get("", response_model=EmploymentPageResponse)
def list_employments(
    student_name: str | None = Query(default=None),
    company: str | None = Query(default=None),
    position: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    filters = [like(Employment.student_name, student_name), like(Employment.company, company), like(Employment.position, position), like(Employment.status, status)]
    return list_with_filters(db, Employment, filters, sort_by, sort_order, page, page_size)


@router.post("", response_model=EmploymentResponse, status_code=status.HTTP_201_CREATED)
def create_employment(payload: EmploymentCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    return create_with_log(db, Employment, payload, user, "employments", "student_name")


@router.get("/{item_id}", response_model=EmploymentResponse)
def get_employment(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return get_by_id(db, Employment, item_id, "就业记录不存在")


@router.put("/{item_id}", response_model=EmploymentResponse)
def update_employment(
    item_id: int,
    payload: EmploymentUpdate,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_teacher),
):
    obj = get_by_id(db, Employment, item_id, "就业记录不存在")
    return update_with_log(db, obj, payload, user, "employments", "student_name")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employment(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, Employment, item_id, "就业记录不存在")
    delete_with_log(db, obj, user, "employments", "student_name")
