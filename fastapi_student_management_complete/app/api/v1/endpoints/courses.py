from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_login, require_teacher
from app.core.database import get_db
from app.models.entities import Course
from app.schemas.entities import CourseCreate, CoursePageResponse, CourseResponse, CourseUpdate
from app.services.entity_service import create_with_log, delete_with_log, get_by_id, list_with_filters, update_with_log
from app.services.query_service import like

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=CoursePageResponse)
def list_courses(
    code: str | None = Query(default=None),
    name: str | None = Query(default=None),
    teacher_name: str | None = Query(default=None),
    credit: float | None = Query(default=None),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    filters = [like(Course.code, code), like(Course.name, name), like(Course.teacher_name, teacher_name)]
    if credit is not None:
        filters.append(Course.credit == credit)
    return list_with_filters(db, Course, filters, sort_by, sort_order, page, page_size)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    duplicate = db.query(Course).filter(Course.code == payload.code).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="课程编码已存在")
    return create_with_log(db, Course, payload, user, "courses", "name")


@router.get("/{item_id}", response_model=CourseResponse)
def get_course(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return get_by_id(db, Course, item_id, "课程不存在")


@router.put("/{item_id}", response_model=CourseResponse)
def update_course(item_id: int, payload: CourseUpdate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, Course, item_id, "课程不存在")
    if payload.code and payload.code != obj.code:
        duplicate = db.query(Course).filter(Course.code == payload.code).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="课程编码已存在")
    return update_with_log(db, obj, payload, user, "courses", "name")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = get_by_id(db, Course, item_id, "课程不存在")
    delete_with_log(db, obj, user, "courses", "name")
