from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import ClassGroup, Course, Employment, Grade, Teacher
from app.models.student import Student


def get_dashboard_stats(db: Session):
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
        "course_scores": [{"course_name": row.course_name, "avg_score": round(float(row.avg_score), 2)} for row in score_by_course],
    }


def get_grade_statistics(db: Session):
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
