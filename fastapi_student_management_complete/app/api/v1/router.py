from fastapi import APIRouter

from app.api.v1.endpoints import admin_users, auth, chat, classes, courses, dashboard, employments, grades, logs, students, teachers

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(dashboard.router)
api_router.include_router(logs.router)
api_router.include_router(students.router)
api_router.include_router(teachers.router)
api_router.include_router(courses.router)
api_router.include_router(classes.router)
api_router.include_router(employments.router)
api_router.include_router(grades.router)
api_router.include_router(admin_users.router)
