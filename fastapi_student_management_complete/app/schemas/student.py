from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class StudentBase(BaseModel):
    student_no: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(..., min_length=1, max_length=10)
    grade: Optional[str] = Field(default=None, min_length=2, max_length=30)
    age: int = Field(..., ge=1, le=120)
    major: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=6, max_length=30)
    email: EmailStr
    enrollment_date: date


class StudentCreate(StudentBase):
    grade: str = Field(..., min_length=2, max_length=30)


class StudentUpdate(BaseModel):
    student_no: Optional[str] = Field(default=None, min_length=3, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    gender: Optional[str] = Field(default=None, min_length=1, max_length=10)
    grade: Optional[str] = Field(default=None, min_length=2, max_length=30)
    age: Optional[int] = Field(default=None, ge=1, le=120)
    major: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, min_length=6, max_length=30)
    email: Optional[EmailStr] = None
    enrollment_date: Optional[date] = None


class StudentResponse(StudentBase):
    id: int

    class Config:
        from_attributes = True


class StudentPageResponse(BaseModel):
    items: list[StudentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
