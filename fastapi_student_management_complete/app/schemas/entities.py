from datetime import date
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class TeacherBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=50)
    department: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=6, max_length=30)
    email: EmailStr


class TeacherCreate(TeacherBase):
    pass


class TeacherUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    title: Optional[str] = Field(default=None, min_length=1, max_length=50)
    department: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, min_length=6, max_length=30)
    email: Optional[EmailStr] = None


class TeacherResponse(TeacherBase):
    id: int

    class Config:
        from_attributes = True


class TeacherPageResponse(BaseModel):
    items: list["TeacherResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class CourseBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    teacher_name: str = Field(..., min_length=1, max_length=100)
    credit: float = Field(..., ge=0.5, le=20)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    teacher_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    credit: Optional[float] = Field(default=None, ge=0.5, le=20)


class CourseResponse(CourseBase):
    id: int

    class Config:
        from_attributes = True


class CoursePageResponse(BaseModel):
    items: list["CourseResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class ClassGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    grade: str = Field(..., min_length=1, max_length=20)
    major: str = Field(..., min_length=1, max_length=100)
    head_teacher: str = Field(..., min_length=1, max_length=100)
    student_count: int = Field(..., ge=1, le=500)


class ClassGroupCreate(ClassGroupBase):
    pass


class ClassGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    grade: Optional[str] = Field(default=None, min_length=1, max_length=20)
    major: Optional[str] = Field(default=None, min_length=1, max_length=100)
    head_teacher: Optional[str] = Field(default=None, min_length=1, max_length=100)
    student_count: Optional[int] = Field(default=None, ge=1, le=500)


class ClassGroupResponse(ClassGroupBase):
    id: int

    class Config:
        from_attributes = True


class ClassGroupPageResponse(BaseModel):
    items: list["ClassGroupResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class EmploymentBase(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=100)
    company: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., min_length=1, max_length=100)
    salary: float = Field(..., ge=0)
    status: str = Field(..., min_length=1, max_length=30)
    employment_date: date


class EmploymentCreate(EmploymentBase):
    pass


class EmploymentUpdate(BaseModel):
    student_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    company: Optional[str] = Field(default=None, min_length=1, max_length=100)
    position: Optional[str] = Field(default=None, min_length=1, max_length=100)
    salary: Optional[float] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, min_length=1, max_length=30)
    employment_date: Optional[date] = None


class EmploymentResponse(EmploymentBase):
    id: int

    class Config:
        from_attributes = True


class EmploymentPageResponse(BaseModel):
    items: list["EmploymentResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class GradeBase(BaseModel):
    student_no: str = Field(..., min_length=1, max_length=50)
    student_name: str = Field(..., min_length=1, max_length=100)
    course_name: str = Field(..., min_length=1, max_length=100)
    score: float = Field(..., ge=0, le=100)
    exam_date: date


class GradeCreate(GradeBase):
    pass


class GradeUpdate(BaseModel):
    student_no: Optional[str] = Field(default=None, min_length=1, max_length=50)
    student_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    course_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    score: Optional[float] = Field(default=None, ge=0, le=100)
    exam_date: Optional[date] = None


class GradeResponse(GradeBase):
    id: int

    class Config:
        from_attributes = True


class GradePageResponse(BaseModel):
    items: list["GradeResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class OperationLogResponse(BaseModel):
    id: int
    username: str
    role: str
    module: str
    action: str
    target_id: Optional[int] = None
    detail: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OperationLogPageResponse(BaseModel):
    items: list["OperationLogResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserAccountBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    role: str = Field(..., pattern="^(admin|teacher|student)$")
    is_active: bool = True


class UserAccountCreate(UserAccountBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserAccountUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserAccountResponse(UserAccountBase):
    id: int

    class Config:
        from_attributes = True


class UserAccountPageResponse(BaseModel):
    items: list["UserAccountResponse"]
    total: int
    page: int
    page_size: int
    total_pages: int
