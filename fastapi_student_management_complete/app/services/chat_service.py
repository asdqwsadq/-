import os

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.integrations.deepseek_client import chat_completion
from app.models.entities import ClassGroup, Course, Employment, Grade, Teacher
from app.models.student import Student


def get_deepseek_key() -> str | None:
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


def _rows_to_text(rows, fields):
    lines = []
    for row in rows:
        item = ", ".join([f"{field}={getattr(row, field)}" for field in fields])
        lines.append(item)
    return "\n".join(lines) if lines else "无数据"


def build_ai_context(db: Session) -> str:
    # 查询所有学生，确保AI能覆盖所有专业（不再限制数量）
    students = db.query(Student).order_by(Student.id.asc()).all()
    teachers = db.query(Teacher).order_by(Teacher.id.desc()).limit(30).all()
    courses = db.query(Course).order_by(Course.id.desc()).limit(30).all()
    classes = db.query(ClassGroup).order_by(ClassGroup.id.desc()).limit(30).all()
    employments = db.query(Employment).order_by(Employment.id.desc()).limit(30).all()
    grades = db.query(Grade).order_by(Grade.id.desc()).limit(50).all()

    # 额外注入专业汇总，确保AI不遗漏任何专业
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


def build_chart_data(db: Session, message: str) -> dict | None:
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
    return None


def ask_ai(db: Session, message: str) -> dict:
    api_key = get_deepseek_key()
    if not api_key:
        raise ValueError("未配置 DEEPSEEK_API_KEY，请先在环境变量中设置")
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
            {"role": "system", "content": build_ai_context(db)},
            {"role": "user", "content": message},
        ],
        "temperature": 0.3,
    }
    answer = chat_completion(api_key, body)
    return {"answer": answer, "chart": build_chart_data(db, message)}
