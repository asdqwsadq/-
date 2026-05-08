from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.audit import write_log
from app.core.database import get_db
from app.core.auth import require_login, require_teacher
from app.crud.student import (
    create_student,
    delete_student,
    get_student,
    get_student_by_no,
    update_student,
)
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate

router = APIRouter(prefix="/api/students", tags=["students"])


def _ensure_grade_column(db: Session):
    columns = [row[1] for row in db.execute(text("PRAGMA table_info(students)")).fetchall()]
    if "grade" not in columns:
        db.execute(text("ALTER TABLE students ADD COLUMN grade VARCHAR(30)"))
        db.commit()


@router.get("")
def list_students(
    student_no: str | None = Query(default=None),
    name: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    major: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    email: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=19, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    _ensure_grade_column(db)
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
    total = query.count()
    items = query.order_by(Student.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def add_student(student_in: StudentCreate, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_teacher)):
    _ensure_grade_column(db)
    existing = get_student_by_no(db, student_in.student_no)
    if existing:
        raise HTTPException(status_code=400, detail="学号已存在")
    user: dict[str, str] = _
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
    _: dict[str, str] = Depends(require_teacher),
):
    _ensure_grade_column(db)
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    if student_in.student_no and student_in.student_no != student.student_no:
        duplicate = get_student_by_no(db, student_in.student_no)
        if duplicate:
            raise HTTPException(status_code=400, detail="学号已存在")

    user = _
    updated = update_student(db, student, student_in)
    write_log(db, user["username"], user["role"], "students", "update", updated.id, updated.name)
    return updated


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student(student_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_teacher)):
    user = _
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    write_log(db, user["username"], user["role"], "students", "delete", student.id, student.name)
    delete_student(db, student)
