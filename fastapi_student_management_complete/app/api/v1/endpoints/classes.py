from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_login, require_teacher
from app.core.database import get_db
from app.models.entities import ClassGroup
from app.schemas.entities import ClassGroupCreate, ClassGroupPageResponse, ClassGroupResponse, ClassGroupUpdate
from app.services.entity_service import create_with_log, delete_with_log, get_by_id, list_with_filters, update_with_log
from app.services.query_service import like

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("", response_model=ClassGroupPageResponse)
def list_classes(
    name: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    major: str | None = Query(default=None),
    head_teacher: str | None = Query(default=None),
    student_count: int | None = Query(default=None),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    filters = [like(ClassGroup.name, name), like(ClassGroup.grade, grade), like(ClassGroup.major, major), like(ClassGroup.head_teacher, head_teacher)]
    if student_count is not None:
        filters.append(ClassGroup.student_count == student_count)
    return list_with_filters(db, ClassGroup, filters, sort_by, sort_order, page, page_size)


@router.post("", response_model=ClassGroupResponse, status_code=status.HTTP_201_CREATED)
def create_class(payload: ClassGroupCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    return create_with_log(db, ClassGroup, payload, user, "classes", "name")


@router.get("/{item_id}", response_model=ClassGroupResponse)
def get_class(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return get_by_id(db, ClassGroup, item_id, "班级不存在")


@router.put("/{item_id}", response_model=ClassGroupResponse)
def update_class(item_id: int, payload: ClassGroupUpdate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, ClassGroup, item_id, "班级不存在")
    return update_with_log(db, obj, payload, user, "classes", "name")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, ClassGroup, item_id, "班级不存在")
    delete_with_log(db, obj, user, "classes", "name")
