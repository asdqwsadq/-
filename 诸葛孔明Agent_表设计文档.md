# 诸葛孔明 Agent 表设计文档

## 1. 设计说明

本系统建议采用 `PostgreSQL + pgvector` 作为主存储方案，`LangChain` 负责检索、记忆和工具编排。

核心目标：

- 维护 Agent 配置
- 维护会话与消息
- 管理四大名著知识库文档与切片
- 记录反馈、检索与审计信息

## 2. 表结构总览

1. `agent_profile` - Agent 基础配置表
2. `conversation_session` - 会话表
3. `conversation_message` - 消息明细表
4. `knowledge_document` - 知识文档表
5. `knowledge_chunk` - 文档切片表
6. `prompt_template` - Prompt 模板表
7. `tool_config` - 工具配置表
8. `user_feedback` - 用户反馈表
9. `retrieval_log` - 检索日志表
10. `audit_log` - 审计日志表

## 3. 详细表设计

### 3.1 Agent 基础配置表 `agent_profile`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| agent_code | varchar(64) | 否 | 否 | 唯一编码，如 `kongming` |
| agent_name | varchar(128) | 否 | 否 | Agent 名称 |
| persona_name | varchar(64) | 否 | 否 | 人设名称，如“诸葛孔明” |
| persona_desc | text | 否 | 否 | 人设描述 |
| model_name | varchar(128) | 否 | 否 | 当前使用模型 |
| temperature | numeric(3,2) | 否 | 否 | 采样温度 |
| max_tokens | int | 否 | 否 | 最大输出长度 |
| status | varchar(32) | 否 | 否 | 状态：active/inactive |
| created_at | timestamp | 否 | 否 | 创建时间 |
| updated_at | timestamp | 否 | 否 | 更新时间 |

索引建议：

- `uk_agent_profile_agent_code(agent_code)` 唯一索引
- `idx_agent_profile_status(status)`

### 3.2 会话表 `conversation_session`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| session_id | varchar(64) | 否 | 否 | 会话唯一标识 |
| user_id | varchar(64) | 否 | 是 | 用户标识 |
| agent_code | varchar(64) | 否 | 否 | 关联 Agent |
| session_title | varchar(128) | 否 | 是 | 会话标题 |
| summary | text | 否 | 是 | 会话摘要 |
| memory_state | jsonb | 否 | 是 | LangChain 记忆状态 |
| status | varchar(32) | 否 | 否 | active/closed |
| last_message_at | timestamp | 否 | 是 | 最近消息时间 |
| created_at | timestamp | 否 | 否 | 创建时间 |
| updated_at | timestamp | 否 | 否 | 更新时间 |

索引建议：

- `uk_conversation_session_session_id(session_id)` 唯一索引
- `idx_conversation_session_user_id(user_id)`
- `idx_conversation_session_agent_code(agent_code)`

### 3.3 消息明细表 `conversation_message`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| message_id | varchar(64) | 否 | 否 | 消息唯一标识 |
| session_id | varchar(64) | 否 | 否 | 会话 ID |
| role | varchar(32) | 否 | 否 | user/assistant/system/tool |
| content | text | 否 | 否 | 消息内容 |
| content_json | jsonb | 否 | 是 | 结构化内容，如工具调用结果 |
| token_count | int | 否 | 是 | Token 数 |
| source_type | varchar(32) | 否 | 是 | manual/rag/tool |
| source_refs | jsonb | 否 | 是 | 来源片段或引用 |
| created_at | timestamp | 否 | 否 | 创建时间 |

索引建议：

- `uk_conversation_message_message_id(message_id)` 唯一索引
- `idx_conversation_message_session_id_created_at(session_id, created_at)`

### 3.4 知识文档表 `knowledge_document`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| doc_id | varchar(64) | 否 | 否 | 文档唯一标识 |
| doc_title | varchar(255) | 否 | 否 | 文档标题 |
| doc_source | varchar(255) | 否 | 是 | 来源路径或 URL |
| corpus_name | varchar(128) | 否 | 否 | 语料名称，如《三国演义》《红楼梦》《西游记》《水浒传》 |
| file_type | varchar(32) | 否 | 否 | txt/pdf/md/docx 等 |
| file_size | bigint | 否 | 是 | 文件大小 |
| checksum | varchar(128) | 否 | 是 | 文件校验值 |
| parse_status | varchar(32) | 否 | 否 | pending/parsed/failed |
| metadata | jsonb | 否 | 是 | 扩展元数据 |
| created_at | timestamp | 否 | 否 | 创建时间 |
| updated_at | timestamp | 否 | 否 | 更新时间 |

索引建议：

- `uk_knowledge_document_doc_id(doc_id)` 唯一索引
- `idx_knowledge_document_corpus_name(corpus_name)`

### 3.5 文档切片表 `knowledge_chunk`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| chunk_id | varchar(64) | 否 | 否 | 切片唯一标识 |
| doc_id | varchar(64) | 否 | 否 | 关联文档 |
| chunk_index | int | 否 | 否 | 切片顺序 |
| chunk_text | text | 否 | 否 | 切片正文 |
| chunk_tokens | int | 否 | 是 | 切片 Token 数 |
| embedding | vector | 否 | 是 | 向量索引字段 |
| metadata | jsonb | 否 | 是 | 章节、页码、段落等信息 |
| created_at | timestamp | 否 | 否 | 创建时间 |

索引建议：

- `uk_knowledge_chunk_chunk_id(chunk_id)` 唯一索引
- `idx_knowledge_chunk_doc_id(doc_id)`
- `idx_knowledge_chunk_embedding` 使用向量索引

### 3.6 Prompt 模板表 `prompt_template`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| template_code | varchar(64) | 否 | 否 | 模板编码 |
| template_name | varchar(128) | 否 | 否 | 模板名称 |
| template_type | varchar(32) | 否 | 否 | persona/rag/tool/system |
| system_prompt | text | 否 | 否 | 系统提示词 |
| user_prompt | text | 否 | 是 | 用户提示词模板 |
| variables | jsonb | 否 | 是 | 模板变量定义 |
| version | varchar(32) | 否 | 否 | 版本号 |
| status | varchar(32) | 否 | 否 | active/inactive |
| created_at | timestamp | 否 | 否 | 创建时间 |
| updated_at | timestamp | 否 | 否 | 更新时间 |

### 3.7 工具配置表 `tool_config`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| tool_code | varchar(64) | 否 | 否 | 工具编码 |
| tool_name | varchar(128) | 否 | 否 | 工具名称 |
| tool_type | varchar(32) | 否 | 否 | search/memory/summary/retrieval |
| config_json | jsonb | 否 | 否 | 工具参数 |
| enabled | boolean | 否 | 否 | 是否启用 |
| created_at | timestamp | 否 | 否 | 创建时间 |
| updated_at | timestamp | 否 | 否 | 更新时间 |

### 3.8 用户反馈表 `user_feedback`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| feedback_id | varchar(64) | 否 | 否 | 反馈唯一标识 |
| session_id | varchar(64) | 否 | 否 | 会话 ID |
| message_id | varchar(64) | 否 | 是 | 对应消息 ID |
| rating | int | 否 | 否 | 评分，1-5 |
| feedback_text | text | 否 | 是 | 用户评价 |
| feedback_type | varchar(32) | 否 | 是 | like/dislike/error/suggestion |
| created_at | timestamp | 否 | 否 | 创建时间 |

### 3.9 检索日志表 `retrieval_log`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| log_id | varchar(64) | 否 | 否 | 日志唯一标识 |
| session_id | varchar(64) | 否 | 否 | 会话 ID |
| query_text | text | 否 | 否 | 检索问题 |
| top_k | int | 否 | 否 | 检索数量 |
| retrieved_chunks | jsonb | 否 | 是 | 命中的切片列表 |
| latency_ms | int | 否 | 是 | 检索耗时 |
| created_at | timestamp | 否 | 否 | 创建时间 |

### 3.10 审计日志表 `audit_log`

| 字段名 | 类型 | 主键 | 允许空 | 说明 |
|---|---|---:|---:|---|
| id | bigint | 是 | 否 | 主键 |
| log_id | varchar(64) | 否 | 否 | 日志唯一标识 |
| operator | varchar(64) | 否 | 是 | 操作人 |
| action | varchar(128) | 否 | 否 | 操作动作 |
| target_type | varchar(64) | 否 | 是 | 目标类型 |
| target_id | varchar(64) | 否 | 是 | 目标 ID |
| detail | jsonb | 否 | 是 | 详细信息 |
| created_at | timestamp | 否 | 否 | 创建时间 |

## 4. 关系说明

- `agent_profile` 1 对多 `conversation_session`
- `conversation_session` 1 对多 `conversation_message`
- `knowledge_document` 1 对多 `knowledge_chunk`
- `conversation_session` 可关联 `user_feedback`、`retrieval_log`

## 5. 建模建议

1. 会话和消息表建议按时间分区或定期归档。
2. `knowledge_chunk.embedding` 由向量数据库或 pgvector 维护。
3. Prompt 和工具配置建议保留版本号，便于回滚。
4. 所有 `*_id` 字段建议使用业务唯一 ID，便于外部系统调用。

