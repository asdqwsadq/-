from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    title = Column(String(50), nullable=False)
    department = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=False)
    email = Column(String(100), nullable=False)


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    teacher_name = Column(String(100), nullable=False)
    credit = Column(Float, nullable=False)


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    grade = Column(String(20), nullable=False)
    major = Column(String(100), nullable=False)
    head_teacher = Column(String(100), nullable=False)
    student_count = Column(Integer, nullable=False)


class Employment(Base):
    __tablename__ = "employments"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String(100), nullable=False)
    company = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)
    salary = Column(Float, nullable=False)
    status = Column(String(30), nullable=False)
    employment_date = Column(Date, nullable=False)


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_no = Column(String(50), nullable=False, index=True)
    student_name = Column(String(100), nullable=False)
    course_name = Column(String(100), nullable=False)
    score = Column(Float, nullable=False)
    exam_date = Column(Date, nullable=False)


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)
    module = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=True)
    detail = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
