# FastAPI 教务管理系统（重构版）

## 1. 改造目标
- 后端从“巨型路由”重构为 `endpoint -> service -> repository` 分层。
- 前端从单文件脚本重构为模块化 ES Modules。
- 修复管理员模块串数据风险：管理员页仅渲染账号结构。
- 日志时间展示支持网络时间校准（客户端联网时间）。
- AI 对话保留并支持图表渲染。

## 2. 目录结构（核心）
```text
app/
├─ api/v1/
│  ├─ router.py
│  └─ endpoints/
│     ├─ auth.py
│     ├─ students.py
│     ├─ teachers.py
│     ├─ courses.py
│     ├─ classes.py
│     ├─ employments.py
│     ├─ grades.py
│     ├─ dashboard.py
│     ├─ chat.py
│     ├─ logs.py
│     └─ admin_users.py
├─ services/
├─ repositories/
├─ integrations/
├─ core/
├─ models/
├─ schemas/
├─ static/js/
│  ├─ bootstrap.js
│  ├─ config/modules.js
│  ├─ services/{auth,http,time}.js
│  └─ features/{chat,logs}.js
└─ templates/index.html
```

## 3. 运行方式
```powershell
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问地址：
- 首页: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- API 文档: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 4. 默认账号
- 管理员：`admin` / `123456`
- 老师：`teacher` / `123456`
- 学生：`student` / `123456`

## 5. 环境变量
- `APP_ADMIN_USERNAME`
- `APP_ADMIN_PASSWORD`
- `APP_TEACHER_USERNAME`
- `APP_TEACHER_PASSWORD`
- `APP_STUDENT_USERNAME`
- `APP_STUDENT_PASSWORD`
- `DEEPSEEK_API_KEY`

## 6. 重构后行为说明
- 管理员模块：
  - 请求接口：`/api/admin/users`
  - 返回结构校验失败时阻止渲染并显示错误。
- 日志模块：
  - 请求接口：`/api/logs`
  - 时间显示使用网络时间偏移校准（失败自动回退本机时间）。
- AI 对话：
  - 请求接口：`/api/chat`
  - 返回 `answer + chart`，前端使用 ECharts 渲染。

## 7. 回归建议
- 切换任意模块后进入“管理员板块”，确认只显示账号数据。
- 登录管理员后刷新日志，观察时间显示连续且合理。
- 在 AI 对话输入“分析成绩并画图”，验证文本和图表均出现。


