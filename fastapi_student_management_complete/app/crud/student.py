from sqlalchemy.orm import Session

from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate


def get_students(db: Session):
    return db.query(Student).order_by(Student.id.desc()).all()


def get_student(db: Session, student_id: int):
    return db.query(Student).filter(Student.id == student_id).first()


def get_student_by_no(db: Session, student_no: str):
    return db.query(Student).filter(Student.student_no == student_no).first()


def create_student(db: Session, student_in: StudentCreate):
    student = Student(**student_in.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student(db: Session, student: Student, student_in: StudentUpdate):
    update_data = student_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student


def delete_student(db: Session, student: Student):
    db.delete(student)
    db.commit()
