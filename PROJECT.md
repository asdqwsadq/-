# 孔明问策（Kongming Agent）项目文档

## 一、项目概述

**孔明问策**是一个以诸葛亮人格驱动的四大名著知识问答系统。用户提问后，系统通过 RAG（检索增强生成）管道，先从向量知识库中检索相关原文片段，再交由 DeepSeek 大模型以诸葛孔明的口吻生成回答，并以 SSE 流式输出到前端。

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite 5 + CSS Grid |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + MySQL |
| 向量库 | Milvus 2.5.6 (Standalone) |
| 嵌入模型 | Ollama `embeddinggemma:300m` (768维) |
| 切片模型 | Ollama `qwen2.5:14b` |
| 对话模型 | DeepSeek Chat API |
| 部署 | Docker Compose (Milvus) + 裸进程 |

---

## 二、项目结构

```
kongming_agent/
├── .env                          # 环境配置（API密钥、数据库连接等）
├── start.sh                      # 一键启动脚本
│
├── backend/                      # Python FastAPI 后端
│   ├── run_backend.py            # 入口：加载.env → uvicorn
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI 工厂函数、CORS、静态文件
│       ├── schemas.py            # Pydantic 请求/响应模型
│       ├── core/
│       │   ├── config.py         # 配置类（从环境变量读取）
│       │   └── database.py       # SQLAlchemy 引擎、会话管理
│       ├── models/
│       │   └── mysql.py          # 9 张 MySQL 表 ORM 模型
│       ├── api/
│       │   ├── v1.py             # 路由聚合器
│       │   ├── agent.py          # 会话 + 消息 + SSE 流式端点
│       │   ├── knowledge.py      # 知识库 CRUD + 异步重建
│       │   ├── health.py         # 健康检查
│       │   ├── feedback.py       # 用户反馈
│       │   └── admin.py          # 管理后台 API
│       └── services/
│           ├── kongming_agent.py     # 核心 RAG 管道 + 流式回答
│           ├── session_service.py    # 数据库 CRUD 层
│           ├── knowledge_base.py     # 向量检索 + 回退方案
│           ├── knowledge_ingestion.py # 文档加载 → 切片 → 向量化 → 写库
│           ├── deepseek_client.py    # DeepSeek API (chat + stream)
│           ├── ollama_client.py      # Ollama (嵌入 + 切片规划)
│           └── milvus_store.py       # Milvus 连接、集合管理、搜索
│
├── frontend/                     # React 前端
│   ├── vite.config.cjs           # Vite 配置（代理 /api → :8000）
│   └── src/
│       ├── main.tsx              # React 入口
│       ├── App.tsx               # 主组件（状态管理、流式渲染）
│       ├── api.ts                # API 封装 + SSE 解析
│       └── styles.css            # 暗色主题 CSS
│
├── admin/                        # 管理后台（独立 React 应用）
│
├── docker/milvus/
│   └── docker-compose.yml        # etcd + MinIO + Milvus
│
├── docs/zhugeliang/              # 诸葛亮文献原文（10篇）
│   ├── 01_三国志_诸葛亮传.txt
│   ├── 02_前出师表.txt
│   ├── 04_诫子书.txt
│   ├── 05_将苑.txt
│   └── ... (共10篇)
│
└── 《三国演义》.txt               # 四大名著全文
    《红楼梦》.txt
    《西游记》.txt
    《水浒传》.txt
```

---

## 三、核心数据流

```
用户输入问题
    │
    ▼
前端 App.tsx handleSend()
    │  POST /api/v1/会话/{id}/消息  {内容, 流式:true}
    ▼
后端 agent.py → kongming_agent.answer_stream()
    │
    ├─ 1. 保存用户消息到 MySQL
    │
    ├─ 2. 实体匹配 _is_four_classics_query(问题)
    │      检查问题是否包含四大名著人物/地点/事件关键词(150+个)
    │      → 不匹配：跳过 RAG，直接调用 LLM
    │
    ├─ 3. 向量检索 knowledge_base.search(问题, top_k=4)
    │      ├─ 问题向量化：ollama_client.embed("embeddinggemma:300m", 问题)
    │      ├─ Milvus ANN 搜索（COSINE 相似度）
    │      └─ 分数过滤：max_score < 0.48 全部丢弃，单条 < 0.45 丢弃
    │
    ├─ 4. 构建系统提示词
    │      ├─ 人物设定：诸葛孔明（来自 agent_profiles 表）
    │      ├─ 回答风格：沉稳、通透、善于概括（来自 prompt_templates 表）
    │      └─ 上下文约束：有资料时严格引用，无资料时用自身学识
    │
    ├─ 5. 组装 messages 数组：[system] + 历史对话 + [user] 当前问题
    │
    └─ 6. deepseek_client.chat_stream(messages)
           └─ POST https://api.deepseek.com/v1/chat/completions
              解析 SSE data: 行，提取 choices[0].delta.content
              逐 token 流式返回
    │
    ▼
后端 SSE StreamingResponse
  data: {"type":"chunk","payload":"孔明"}
  data: {"type":"chunk","payload":"以为"}
  ...
  data: {"type":"done","payload":{...sources...}}
    │
    ▼
前端 api.ts ReadableStream 解析
  → App.tsx 逐字更新界面
```

---

## 四、关键设计

### 4.1 多层 RAG 过滤

1. **实体匹配**：问题必须包含四大名著相关关键词（诸葛亮、孙悟空、大观园等 150+ 个），否则不触发检索
2. **最高分阈值 0.48**：最高相似度不足 0.48，说明检索结果不可靠，全部丢弃
3. **单条阈值 0.45**：过滤低分噪音

### 4.2 流式输出 (SSE)

- 后端用 `fastapi.responses.StreamingResponse` 包装异步生成器
- SSE 格式：`data: {"type": "chunk"|"done"|"error", "payload": ...}\n\n`
- 前端用 `fetch` + `ReadableStream` 逐行解析（不用 EventSource，因为 EventSource 不支持 POST）

### 4.3 嵌入模型切换

从阿里云 DashScope (`text-embedding-v4`, 1024维) 切换为本地 Ollama (`embeddinggemma:300m`, 768维)：
- 维度不兼容，必须删除旧 Milvus 集合并全量重建
- 14 篇文档 → 约 2977 个向量块 → 单次全量写入 Milvus

### 4.4 文档切片策略

1. 按"第X回/章/节"正则分割
2. 每块 ≤ 12000 字
3. 可选 LLM 辅助切片（qwen2.5:14b，需开启 `USE_LLM_CHUNK_PLANNING=1`）
4. 默认启发式滑动窗口（目标 1200 字，最大 1800 字）

### 4.5 知识库文档

| 类别 | 文件 | 大小 |
|------|------|------|
| 四大名著 | 《三国演义》《红楼梦》《西游记》《水浒传》 | 1.7-2.8 MB |
| 诸葛亮文献 | 三国志·诸葛亮传、前后出师表、诫子书、将苑、便宜十六策等 10 篇 | 几 KB ~ 48 KB |

---

## 五、数据库表

### MySQL（关系数据）

| 表名 | 用途 |
|------|------|
| `agent_profiles` | 智能体配置（人格名、描述、模型参数） |
| `sessions` | 会话记录 |
| `messages` | 消息记录（问题、回答、来源引用） |
| `knowledge_documents` | 已入库文档登记 |
| `retrieval_logs` | 检索日志（问题、命中、延迟） |
| `feedback` | 用户反馈（1-5 评分） |
| `jobs` | 异步任务（知识库重建进度） |
| `prompt_templates` | 提示词模板 |
| `app_meta` | 应用元数据 |

### Milvus（向量数据）

集合 `four_classics_chunks`，字段：
- `chunk_id`（主键）、`corpus_name`、`doc_title`、`chunk_text`
- `embedding`（FLOAT_VECTOR, 768 维）
- 索引：AUTOINDEX, COSINE 相似度

---

## 六、启动方式

### 前置条件
- Docker Desktop（运行 Milvus）
- Ollama（本地嵌入和切片模型）
- Node.js 18+
- Python 3.11+ (miniconda env `myenv`)
- MySQL 8.0+

### 一键启动
```bash
./start.sh
```

### 手动启动
```bash
# 1. 启动 Milvus
cd docker/milvus && docker compose up -d

# 2. 启动后端
cd backend
python run_backend.py    # 监听 :8000

# 3. 启动前端
cd frontend
npm install && npm run dev    # 监听 :5173
```

### 首次使用
1. 确保 Ollama 已拉取模型：`ollama pull embeddinggemma:300m && ollama pull qwen2.5:14b`
2. 将四大名著 TXT 和诸葛亮文献放入项目根目录
3. 触发知识库重建：`POST http://127.0.0.1:8000/api/v1/知识库/重建`
4. 访问 http://localhost:5173 开始提问

---

## 七、API 端点速查

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/健康` | 健康检查 |
| `POST` | `/api/v1/智能体/kongming/会话` | 创建会话 |
| `POST` | `/api/v1/会话/{id}/消息` | 发送消息（支持流式 `{流式:true}`） |
| `GET` | `/api/v1/会话/{id}/消息` | 获取历史消息 |
| `GET` | `/api/v1/知识库/检索` | 知识库搜索 |
| `POST` | `/api/v1/知识库/重建` | 触发全量重建（异步） |
| `GET` | `/api/v1/知识库/重建/{job_id}` | 查询重建进度 |
| `GET` | `/api/v1/知识库/诊断` | 诊断检查 |
| `POST` | `/api/v1/反馈` | 提交反馈 |
| `GET` | `/api/v1/管理/概览` | 管理后台概览 |

所有中文端点均有英文别名（如 `/sessions/{id}`、`/knowledge/search`）。

---

## 八、配置说明（.env 关键项）

```
# 模型配置
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHUNK_MODEL=qwen2.5:14b
OLLAMA_EMBEDDING_MODEL=embeddinggemma:300m
EMBEDDING_DIM=768

# LLM
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_CHAT_MODEL=deepseek-chat

# 向量库
MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=four_classics_chunks

# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=xxx
MYSQL_DATABASE=kongming_agent

# 切片参数
CHUNK_TARGET_SIZE=1200
CHUNK_MAX_SIZE=1800
```
