from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_login, require_teacher
from app.core.database import get_db
from app.models.entities import Teacher
from app.schemas.entities import TeacherCreate, TeacherPageResponse, TeacherResponse, TeacherUpdate
from app.services.entity_service import create_with_log, delete_with_log, get_by_id, list_with_filters, update_with_log
from app.services.query_service import like

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("", response_model=TeacherPageResponse)
def list_teachers(
    name: str | None = Query(default=None),
    title: str | None = Query(default=None),
    department: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    email: str | None = Query(default=None),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    filters = [like(Teacher.name, name), like(Teacher.title, title), like(Teacher.department, department), like(Teacher.phone, phone), like(Teacher.email, email)]
    return list_with_filters(db, Teacher, filters, sort_by, sort_order, page, page_size)


@router.post("", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    return create_with_log(db, Teacher, payload, user, "teachers", "name")


@router.get("/{item_id}", response_model=TeacherResponse)
def get_teacher(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return get_by_id(db, Teacher, item_id, "教师不存在")


@router.put("/{item_id}", response_model=TeacherResponse)
def update_teacher(item_id: int, payload: TeacherUpdate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, Teacher, item_id, "教师不存在")
    return update_with_log(db, obj, payload, user, "teachers", "name")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, Teacher, item_id, "教师不存在")
    delete_with_log(db, obj, user, "teachers", "name")
