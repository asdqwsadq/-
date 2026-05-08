import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.api.student import router as student_router
from app.core.database import Base, engine

# 👇 这一行是关键！必须导入所有模型，否则表创建不出来
from app import models

# 项目启动时自动创建所有数据库表
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting database initialization...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete.")
    yield

# 创建 FastAPI 应用
app = FastAPI(
    title="Student Management System",
    version="1.0.0",
    lifespan=lifespan
)

# 注册学生路由
app.include_router(student_router)

# 模板与静态文件配置
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 首页路由
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)
