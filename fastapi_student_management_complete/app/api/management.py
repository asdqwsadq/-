import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import write_log
from app.core.auth import login, require_admin, require_login, require_teacher
from app.core.database import get_db
from app.models.entities import ClassGroup, Course, Employment, Grade, OperationLog, Teacher, UserAccount
from app.models.student import Student
from app.schemas.entities import (
    ClassGroupCreate,
    ClassGroupResponse,
    ClassGroupUpdate,
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    EmploymentCreate,
    EmploymentResponse,
    EmploymentUpdate,
    GradeCreate,
    GradeResponse,
    GradeUpdate,
    OperationLogResponse,
    TeacherCreate,
    TeacherResponse,
    TeacherUpdate,
    UserAccountCreate,
    UserAccountResponse,
    UserAccountUpdate,
)

router = APIRouter(prefix="/api", tags=["management"])


def _get_deepseek_key() -> str | None:
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        return key
    try:
        import winreg  # type: ignore

        registry = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
        value, _ = winreg.QueryValueEx(registry, "DEEPSEEK_API_KEY")
        if isinstance(value, str) and value.strip():
            return value.strip()
    except Exception:
        return None
    return None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    chart: dict | None = None


def _build_chart_data(db: Session, message: str) -> dict | None:
    text = message.lower()
    if any(key in text for key in ["就业", "employ", "公司", "岗位"]):
        rows = (
            db.query(Employment.status, func.count(Employment.id).label("count"))
            .group_by(Employment.status)
            .order_by(func.count(Employment.id).desc())
            .all()
        )
        if not rows:
            return None
        labels = [row.status or "未知" for row in rows]
        values = [int(row.count) for row in rows]
        return {
            "type": "bar",
            "option": {
                "title": {"text": "就业状态分布"},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": labels},
                "yAxis": {"type": "value"},
                "series": [{"type": "bar", "data": values, "name": "人数"}],
            },
        }
    if any(key in text for key in ["成绩", "score", "课程", "grade"]):
        rows = (
            db.query(Grade.course_name, func.avg(Grade.score).label("avg_score"))
            .group_by(Grade.course_name)
            .order_by(func.avg(Grade.score).desc())
            .all()
        )
        if not rows:
            return None
        labels = [row.course_name or "未命名课程" for row in rows]
        values = [round(float(row.avg_score), 2) for row in rows]
        return {
            "type": "line",
            "option": {
                "title": {"text": "课程平均成绩"},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": labels},
                "yAxis": {"type": "value", "min": 0, "max": 100},
                "series": [{"type": "line", "data": values, "name": "平均分", "smooth": True}],
            },
        }
    if any(key in text for key in ["概览", "统计", "总览", "dashboard"]):
        student_total = db.query(func.count(Student.id)).scalar() or 0
        teacher_count = db.query(func.count(Teacher.id)).scalar() or 0
        course_count = db.query(func.count(Course.id)).scalar() or 0
        class_count = db.query(func.count(ClassGroup.id)).scalar() or 0
        return {
            "type": "bar",
            "option": {
                "title": {"text": "教务基础规模概览"},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": ["学生", "老师", "课程", "班级"]},
                "yAxis": {"type": "value"},
                "series": [
                    {"type": "bar", "data": [student_total, teacher_count, course_count, class_count], "name": "数量"}
                ],
            },
        }
    return None


def _build_ai_context(db: Session) -> str:
    # 查询所有学生，确保AI能覆盖所有专业（不再限制数量）
    students = db.query(Student).order_by(Student.id.asc()).all()
    teachers = db.query(Teacher).order_by(Teacher.id.desc()).limit(30).all()
    courses = db.query(Course).order_by(Course.id.desc()).limit(30).all()
    classes = db.query(ClassGroup).order_by(ClassGroup.id.desc()).limit(30).all()
    employments = db.query(Employment).order_by(Employment.id.desc()).limit(30).all()
    grades = db.query(Grade).order_by(Grade.id.desc()).limit(50).all()

    # 额外注入专业汇总 + 专业->学生映射表
    major_stats = (
        db.query(Student.major, func.count(Student.id).label("cnt"))
        .group_by(Student.major)
        .order_by(func.count(Student.id).desc())
        .all()
    )
    major_summary = ", ".join(f"{m.major}({m.cnt}人)" for m in major_stats)

    # 构建专业->学生映射，让AI快速定位每个专业的学生
    major_to_students: dict[str, list[str]] = {}
    for s in students:
        major_to_students.setdefault(s.major, []).append(
            f"id={s.id}, {s.name}({s.student_no})"
        )
    major_detail_lines = []
    for m in major_stats:
        names = major_to_students.get(m.major, [])
        major_detail_lines.append(f"{m.major}: {'; '.join(names)}")

    def _rows_to_text(rows, fields):
        lines = []
        for row in rows:
            item = ", ".join([f"{field}={getattr(row, field)}" for field in fields])
            lines.append(item)
        return "\n".join(lines) if lines else "无数据"

    return (
        "以下是当前系统数据库的业务数据，请基于这些数据回答："
        "\n【重要】[专业-学生对照表]是查询专业时的权威依据，请优先据此回答。"
        f"\n\n[专业-学生对照表]\n{chr(10).join(major_detail_lines)}"
        f"\n\n[专业人数汇总]\n{major_summary}"
        f"\n[总学生数] {len(students)}人"
        f"\n\n[学生明细]\n{_rows_to_text(students, ['id', 'student_no', 'name', 'gender', 'grade', 'major'])}"
        f"\n\n[老师]\n{_rows_to_text(teachers, ['id', 'name', 'title', 'department'])}"
        f"\n\n[课程]\n{_rows_to_text(courses, ['id', 'code', 'name', 'teacher_name', 'credit'])}"
        f"\n\n[班级]\n{_rows_to_text(classes, ['id', 'name', 'grade', 'major', 'student_count'])}"
        f"\n\n[就业]\n{_rows_to_text(employments, ['id', 'student_name', 'company', 'position', 'status'])}"
        f"\n\n[成绩]\n{_rows_to_text(grades, ['id', 'student_no', 'student_name', 'course_name', 'score'])}"
    )


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/login", response_model=LoginResponse)
def user_login(payload: LoginRequest, db: Session = Depends(get_db)):
    result = login(db, payload.username, payload.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    return result


@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(payload: ChatRequest, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    api_key = _get_deepseek_key()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="未配置 DEEPSEEK_API_KEY，请先在环境变量中设置",
        )

    body = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是大学教务管理系统AI助手。"
                    "\n【核心规则】必须严格依据[专业-学生对照表]和[专业人数汇总]回答专业相关问题。"
                    "\n- 当用户查询某专业的学生时，直接从[专业-学生对照表]中查找该专业对应的学生列表。"
                    "\n- 绝不能说某个专业不存在，除非[专业人数汇总]中没有该专业名称。"
                    "\n- 数据是完整的、权威的，不要因为数据量大而遗漏或否认任何记录。"
                    "\n回答要简洁准确，必要时给出可执行建议。"
                ),
            },
            {"role": "system", "content": _build_ai_context(db)},
            {"role": "user", "content": payload.message},
        ],
        "temperature": 0.3,
    }
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用异常: {exc}") from exc

    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise HTTPException(status_code=502, detail="DeepSeek 返回内容为空")
    chart = _build_chart_data(db, payload.message)
    return {"answer": content.strip(), "chart": chart}


def _list_entities(db: Session, model):
    return db.query(model).order_by(model.id.desc()).all()


def _get_entity(db: Session, model, item_id: int):
    return db.query(model).filter(model.id == item_id).first()


def _create_entity(db: Session, model, payload):
    obj = model(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _update_entity(db: Session, obj, payload):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def _delete_entity(db: Session, obj):
    db.delete(obj)
    db.commit()


def _like(field, value: str | None):
    if not value:
        return None
    return field.like(f"%{value}%")


@router.get("/teachers")
def list_teachers(
    name: str | None = Query(default=None),
    title: str | None = Query(default=None),
    department: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    email: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=19, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    query = db.query(Teacher)
    for cond in [
        _like(Teacher.name, name),
        _like(Teacher.title, title),
        _like(Teacher.department, department),
        _like(Teacher.phone, phone),
        _like(Teacher.email, email),
    ]:
        if cond is not None:
            query = query.filter(cond)
    total = query.count()
    items = query.order_by(Teacher.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/teachers", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _create_entity(db, Teacher, payload)
    write_log(db, user["username"], user["role"], "teachers", "create", obj.id, obj.name)
    return obj


@router.get("/teachers/{item_id}", response_model=TeacherResponse)
def get_teacher(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    obj = _get_entity(db, Teacher, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="教师不存在")
    return obj


@router.put("/teachers/{item_id}", response_model=TeacherResponse)
def update_teacher(item_id: int, payload: TeacherUpdate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, Teacher, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="教师不存在")
    updated = _update_entity(db, obj, payload)
    write_log(db, user["username"], user["role"], "teachers", "update", updated.id, updated.name)
    return updated


@router.delete("/teachers/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, Teacher, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="教师不存在")
    write_log(db, user["username"], user["role"], "teachers", "delete", obj.id, obj.name)
    _delete_entity(db, obj)


@router.get("/courses")
def list_courses(
    code: str | None = Query(default=None),
    name: str | None = Query(default=None),
    teacher_name: str | None = Query(default=None),
    credit: float | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=19, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    query = db.query(Course)
    for cond in [
        _like(Course.code, code),
        _like(Course.name, name),
        _like(Course.teacher_name, teacher_name),
    ]:
        if cond is not None:
            query = query.filter(cond)
    if credit is not None:
        query = query.filter(Course.credit == credit)
    total = query.count()
    items = query.order_by(Course.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    duplicate = db.query(Course).filter(Course.code == payload.code).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="课程编码已存在")
    obj = _create_entity(db, Course, payload)
    write_log(db, user["username"], user["role"], "courses", "create", obj.id, obj.name)
    return obj


@router.get("/courses/{item_id}", response_model=CourseResponse)
def get_course(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    obj = _get_entity(db, Course, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="课程不存在")
    return obj


@router.put("/courses/{item_id}", response_model=CourseResponse)
def update_course(item_id: int, payload: CourseUpdate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, Course, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="课程不存在")
    if payload.code and payload.code != obj.code:
        duplicate = db.query(Course).filter(Course.code == payload.code).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="课程编码已存在")
    updated = _update_entity(db, obj, payload)
    write_log(db, user["username"], user["role"], "courses", "update", updated.id, updated.name)
    return updated


@router.delete("/courses/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, Course, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="课程不存在")
    write_log(db, user["username"], user["role"], "courses", "delete", obj.id, obj.name)
    _delete_entity(db, obj)


@router.get("/classes")
def list_classes(
    name: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    major: str | None = Query(default=None),
    head_teacher: str | None = Query(default=None),
    student_count: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=19, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    query = db.query(ClassGroup)
    for cond in [
        _like(ClassGroup.name, name),
        _like(ClassGroup.grade, grade),
        _like(ClassGroup.major, major),
        _like(ClassGroup.head_teacher, head_teacher),
    ]:
        if cond is not None:
            query = query.filter(cond)
    if student_count is not None:
        query = query.filter(ClassGroup.student_count == student_count)
    total = query.count()
    items = query.order_by(ClassGroup.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/classes", response_model=ClassGroupResponse, status_code=status.HTTP_201_CREATED)
def create_class(payload: ClassGroupCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _create_entity(db, ClassGroup, payload)
    write_log(db, user["username"], user["role"], "classes", "create", obj.id, obj.name)
    return obj


@router.get("/classes/{item_id}", response_model=ClassGroupResponse)
def get_class(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    obj = _get_entity(db, ClassGroup, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="班级不存在")
    return obj


@router.put("/classes/{item_id}", response_model=ClassGroupResponse)
def update_class(item_id: int, payload: ClassGroupUpdate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, ClassGroup, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="班级不存在")
    updated = _update_entity(db, obj, payload)
    write_log(db, user["username"], user["role"], "classes", "update", updated.id, updated.name)
    return updated


@router.delete("/classes/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, ClassGroup, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="班级不存在")
    write_log(db, user["username"], user["role"], "classes", "delete", obj.id, obj.name)
    _delete_entity(db, obj)


@router.get("/employments")
def list_employments(
    student_name: str | None = Query(default=None),
    company: str | None = Query(default=None),
    position: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=19, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    query = db.query(Employment)
    for cond in [
        _like(Employment.student_name, student_name),
        _like(Employment.company, company),
        _like(Employment.position, position),
        _like(Employment.status, status),
    ]:
        if cond is not None:
            query = query.filter(cond)
    total = query.count()
    items = query.order_by(Employment.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/employments", response_model=EmploymentResponse, status_code=status.HTTP_201_CREATED)
def create_employment(payload: EmploymentCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _create_entity(db, Employment, payload)
    write_log(db, user["username"], user["role"], "employments", "create", obj.id, obj.student_name)
    return obj


@router.get("/employments/{item_id}", response_model=EmploymentResponse)
def get_employment(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    obj = _get_entity(db, Employment, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="就业记录不存在")
    return obj


@router.put("/employments/{item_id}", response_model=EmploymentResponse)
def update_employment(
    item_id: int,
    payload: EmploymentUpdate,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_teacher),
):
    obj = _get_entity(db, Employment, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="就业记录不存在")
    updated = _update_entity(db, obj, payload)
    write_log(db, user["username"], user["role"], "employments", "update", updated.id, updated.student_name)
    return updated


@router.delete("/employments/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employment(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, Employment, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="就业记录不存在")
    write_log(db, user["username"], user["role"], "employments", "delete", obj.id, obj.student_name)
    _delete_entity(db, obj)


@router.get("/grades")
def list_grades(
    student_no: str | None = Query(default=None),
    student_name: str | None = Query(default=None),
    course_name: str | None = Query(default=None),
    score: float | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=19, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_login),
):
    query = db.query(Grade)
    for cond in [
        _like(Grade.student_no, student_no),
        _like(Grade.student_name, student_name),
        _like(Grade.course_name, course_name),
    ]:
        if cond is not None:
            query = query.filter(cond)
    if score is not None:
        query = query.filter(Grade.score == score)
    total = query.count()
    items = query.order_by(Grade.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/grades", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(payload: GradeCreate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _create_entity(db, Grade, payload)
    write_log(db, user["username"], user["role"], "grades", "create", obj.id, obj.student_name)
    return obj


@router.get("/grades/{item_id}", response_model=GradeResponse)
def get_grade(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    obj = _get_entity(db, Grade, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    return obj


@router.put("/grades/{item_id}", response_model=GradeResponse)
def update_grade(item_id: int, payload: GradeUpdate, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, Grade, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    updated = _update_entity(db, obj, payload)
    write_log(db, user["username"], user["role"], "grades", "update", updated.id, updated.student_name)
    return updated


@router.delete("/grades/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_teacher)):
    obj = _get_entity(db, Grade, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    write_log(db, user["username"], user["role"], "grades", "delete", obj.id, obj.student_name)
    _delete_entity(db, obj)


@router.get("/grades/statistics")
def grade_statistics(db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    count = db.query(func.count(Grade.id)).scalar() or 0
    if count == 0:
        return {"count": 0, "avg_score": 0, "max_score": 0, "min_score": 0, "pass_rate": 0}

    avg_score = db.query(func.avg(Grade.score)).scalar() or 0
    max_score = db.query(func.max(Grade.score)).scalar() or 0
    min_score = db.query(func.min(Grade.score)).scalar() or 0
    pass_count = db.query(func.count(Grade.id)).filter(Grade.score >= 60).scalar() or 0

    return {
        "count": count,
        "avg_score": round(float(avg_score), 2),
        "max_score": float(max_score),
        "min_score": float(min_score),
        "pass_rate": round(pass_count * 100 / count, 2),
    }


@router.get("/grade-statistics")
def grade_stats_alias(db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    return grade_statistics(db, _)


@router.get("/dashboard-stats")
def dashboard_stats(db: Session = Depends(get_db), _: dict[str, str] = Depends(require_login)):
    student_total = db.query(func.count(Student.id)).scalar() or 0
    teacher_count = db.query(func.count(Teacher.id)).scalar() or 0
    course_count = db.query(func.count(Course.id)).scalar() or 0
    class_count = db.query(func.count(ClassGroup.id)).scalar() or 0
    employment_count = db.query(func.count(Employment.id)).scalar() or 0
    grade_count = db.query(func.count(Grade.id)).scalar() or 0
    employed_students = db.query(func.count(func.distinct(Employment.student_name))).scalar() or 0
    employment_rate = round((employed_students * 100 / student_total), 2) if student_total else 0
    avg_score = db.query(func.avg(Grade.score)).scalar() or 0

    score_by_course = (
        db.query(Grade.course_name, func.avg(Grade.score).label("avg_score"))
        .group_by(Grade.course_name)
        .order_by(func.avg(Grade.score).desc())
        .all()
    )
    return {
        "overview": {
            "students": student_total,
            "teachers": teacher_count,
            "courses": course_count,
            "classes": class_count,
            "employments": employment_count,
            "grades": grade_count,
            "employment_rate": employment_rate,
            "avg_score": round(float(avg_score), 2) if avg_score else 0,
        },
        "course_scores": [
            {"course_name": row.course_name, "avg_score": round(float(row.avg_score), 2)}
            for row in score_by_course
        ],
    }


@router.get("/logs")
def list_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=19, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_admin),
):
    query = db.query(OperationLog)
    total = query.count()
    items = query.order_by(OperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/admin/users")
def list_admin_users(
    username: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=19, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_admin),
):
    query = db.query(UserAccount)
    if username:
        query = query.filter(UserAccount.username.like(f"%{username}%"))
    if role:
        query = query.filter(UserAccount.role == role)
    if is_active is not None:
        query = query.filter(UserAccount.is_active == is_active)
    total = query.count()
    items = query.order_by(UserAccount.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/admin/users", response_model=UserAccountResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: UserAccountCreate,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_admin),
):
    exists = db.query(UserAccount).filter(UserAccount.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="账号已存在")
    obj = UserAccount(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    write_log(db, user["username"], user["role"], "admin_users", "create", obj.id, f"新建账号 {obj.username}")
    return obj


@router.get("/admin/users/{item_id}", response_model=UserAccountResponse)
def get_admin_user(
    item_id: int,
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_admin),
):
    obj = db.query(UserAccount).filter(UserAccount.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="账号不存在")
    return obj


@router.put("/admin/users/{item_id}", response_model=UserAccountResponse)
def update_admin_user(
    item_id: int,
    payload: UserAccountUpdate,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_admin),
):
    obj = db.query(UserAccount).filter(UserAccount.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="账号不存在")
    if payload.username and payload.username != obj.username:
        duplicate = db.query(UserAccount).filter(UserAccount.username == payload.username).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="账号已存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    write_log(db, user["username"], user["role"], "admin_users", "update", obj.id, f"更新账号 {obj.username}")
    return obj


@router.delete("/admin/users/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_user(
    item_id: int,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_admin),
):
    obj = db.query(UserAccount).filter(UserAccount.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="账号不存在")
    if obj.username == user["username"]:
        raise HTTPException(status_code=400, detail="不能删除当前登录管理员")
    write_log(db, user["username"], user["role"], "admin_users", "delete", obj.id, f"删除账号 {obj.username}")
    db.delete(obj)
    db.commit()
