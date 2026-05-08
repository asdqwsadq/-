from sqlalchemy import Column, Date, Integer, String

from app.core.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    gender = Column(String(10), nullable=False)
    grade = Column(String(30), nullable=True)
    age = Column(Integer, nullable=False)
    major = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=False)
    email = Column(String(100), nullable=False)
    enrollment_date = Column(Date, nullable=False)
