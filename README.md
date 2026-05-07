# Kongming Agent

诸葛亮智能问答系统。基于 FastAPI + React + Milvus + DashScope + DeepSeek，支持四大名著知识问答。

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy + MySQL
- **前端**: React 18 + TypeScript + Vite 5
- **向量库**: Milvus（Docker 本地部署）
- **向量模型**: DashScope text-embedding-v4（阿里灵积）
- **对话模型**: DeepSeek Chat（DeepSeek API）
- **文档切片**: 快速规则切片（支持可选 LLM 辅助切片）

## 环境要求

- Python 3.10+
- Node.js 18+
- Docker（运行 Milvus）
- MySQL 8.0+

## 启动前准备

### 1. 配置环境变量

复制 `.env.example` 为 `.env`，填入真实值：

```bash
# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=wu1364382646
MYSQL_DATABASE=kongming_agent

# DashScope（用于文本向量化）
DASHSCOPE_API_KEY=你的DashScope key

# DeepSeek（用于对话生成）
DEEPSEEK_API_KEY=你的DeepSeek API key
```

### 2. 启动 Milvus

```bash
cd docker/milvus
docker compose up -d
```

### 3. 初始化数据库

确保 MySQL 中已创建 `kongming_agent` 数据库。后端首次启动时会自动建表。

## 一键启动

```bash
./start.sh
```

此命令会依次：启动 Milvus → 启动后端 → 启动前端开发服务器。按 `Ctrl+C` 停止前端后，后端进程也会退出。

## 分步启动

### 4. 安装后端依赖并启动

```bash
cd backend
pip install -r requirements.txt
python run_backend.py
```

后端将在 `http://127.0.0.1:8000` 启动。

### 5. 构建并启动前端（开发模式）

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器在 `http://127.0.0.1:5173`，需配合后端一起使用。

### 6. 构建前端（生产模式）

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/`。

### 7. 触发知识库重建

后端启动后，调用以下接口将四大名著文本入库：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/rebuild
```

或在浏览器中打开 `http://127.0.0.1:8000/docs` 通过 Swagger UI 调用。

### 8. 启动管理后台（开发模式）

```bash
cd admin
npm install
npm run dev
```

管理后台在 `http://127.0.0.1:5174`。

## 快速启动（日常使用）

如果所有依赖已经就绪，只需：

```bash
# 1. 确保 Milvus 在运行
cd docker/milvus && docker compose up -d

# 2. 启动后端
cd backend && python run_backend.py

# 3. 另开终端，启动前端
cd frontend && npm run dev
```

浏览器打开 `http://localhost:5173` 即可开始问答。

## API 文档

后端启动后：
- Swagger UI: `http://127.0.0.1:8000/docs`
- API 基础地址: `http://127.0.0.1:8000/api/v1`

## 目录结构

```
kongming_agent/
├── backend/           # Python 后端（FastAPI API + 知识库管线）
│   ├── app/
│   │   ├── main.py       # 入口
│   │   ├── core/         # 配置、数据库连接
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── routers/      # API 路由
│   │   └── services/     # 服务层（知识库、会话、DeepSeek 等）
│   └── run_backend.py    # 启动脚本
├── frontend/          # 用户端对话前端（React + Vite）
├── admin/             # 管理后台前端（React + Vite）
├── docker/
│   └── milvus/        # Milvus Docker Compose
├── *.txt              # 四大名著原文
└── 诸葛孔明Agent_*.md  # 设计文档
```
