from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import write_log
from app.core.auth import require_login, require_teacher
from app.core.database import get_db
from app.crud.student import create_student, delete_student, get_student, get_student_by_no, update_student
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentPageResponse, StudentResponse, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=StudentPageResponse)
def list_students(
    student_no: str | None = Query(default=None),
    name: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    major: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    email: str | None = Query(default=None),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    query = db.query(Student)
    if student_no:
        query = query.filter(Student.student_no.like(f"%{student_no}%"))
    if name:
        query = query.filter(Student.name.like(f"%{name}%"))
    if gender:
        query = query.filter(Student.gender.like(f"%{gender}%"))
    if grade:
        query = query.filter(Student.grade.like(f"%{grade}%"))
    if major:
        query = query.filter(Student.major.like(f"%{major}%"))
    if phone:
        query = query.filter(Student.phone.like(f"%{phone}%"))
    if email:
        query = query.filter(Student.email.like(f"%{email}%"))
    sort_column = getattr(Student, sort_by, Student.id)
    order_by = sort_column.desc() if sort_order.lower() != "asc" else sort_column.asc()
    ordered_query = query.order_by(order_by)
    total = ordered_query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    items = ordered_query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def add_student(student_in: StudentCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    existing = get_student_by_no(db, student_in.student_no)
    if existing:
        raise HTTPException(status_code=400, detail="学号已存在")
    student = create_student(db, student_in)
    write_log(db, user["username"], user["role"], "students", "create", student.id, student.name)
    return student


@router.get("/{student_id}", response_model=StudentResponse)
def get_student_detail(student_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return student


@router.put("/{student_id}", response_model=StudentResponse)
def edit_student(
    student_id: int,
    student_in: StudentUpdate,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_teacher),
):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student_in.student_no and student_in.student_no != student.student_no:
        duplicate = get_student_by_no(db, student_in.student_no)
        if duplicate:
            raise HTTPException(status_code=400, detail="学号已存在")
    updated = update_student(db, student, student_in)
    write_log(db, user["username"], user["role"], "students", "update", updated.id, updated.name)
    return updated


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student(student_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    write_log(db, user["username"], user["role"], "students", "delete", student.id, student.name)
    delete_student(db, student)
