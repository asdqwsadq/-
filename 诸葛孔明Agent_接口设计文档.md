# 诸葛孔明 Agent 接口设计文档

## 1. 接口约定

- 基础路径：`/api/v1`
- 数据格式：`application/json`
- 时间格式：`ISO 8601`
- 通用返回结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

## 2. 通用错误码

| 错误码 | 说明 |
|---:|---|
| 0 | 成功 |
| 40001 | 参数错误 |
| 40101 | 未认证 |
| 40301 | 无权限 |
| 40401 | 资源不存在 |
| 40901 | 资源冲突 |
| 42901 | 请求过于频繁 |
| 50001 | 服务内部错误 |

## 3. 核心接口

### 3.1 创建会话

- `POST /agents/{agent_code}/sessions`

请求体：

```json
{
  "user_id": "u10086",
  "title": "四大名著问答",
  "metadata": {
    "scene": "history_chat"
  }
}
```

响应体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "s_202605060001",
    "agent_code": "kongming",
    "status": "active"
  }
}
```

### 3.2 发送消息并获取回复

- `POST /sessions/{session_id}/messages`

请求体：

```json
{
  "content": "孙悟空为什么大闹天宫？",
  "stream": false,
  "options": {
    "top_k": 5,
    "use_rag": true
  }
}
```

响应体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "message_id": "m_001",
    "session_id": "s_202605060001",
    "answer": "亮以为...",
    "sources": [
      {
        "doc_title": "《西游记》",
        "chunk_id": "c_1024",
        "excerpt": "..."
      }
    ],
    "usage": {
      "prompt_tokens": 820,
      "completion_tokens": 210,
      "total_tokens": 1030
    }
  }
}
```

说明：

- `use_rag=true` 时，接口应先检索知识库再生成回答
- `stream=true` 时，建议使用 SSE 或 WebSocket 流式输出

### 3.3 获取会话详情

- `GET /sessions/{session_id}`

响应内容包含：

- 会话基础信息
- 最近摘要
- 最后更新时间

### 3.4 获取会话消息列表

- `GET /sessions/{session_id}/messages?page=1&page_size=20`

响应内容包含：

- 用户消息
- Assistant 回复
- 工具调用结果
- 来源引用

### 3.5 更新会话状态

- `PATCH /sessions/{session_id}`

请求体：

```json
{
  "status": "closed",
  "title": "赤壁之问"
}
```

### 3.6 获取 Agent 配置

- `GET /agents/{agent_code}/config`

返回内容建议包括：

- 人设名称
- 模型名称
- 温度
- 最大输出
- Prompt 模板版本
- 是否启用 RAG

### 3.7 更新 Agent 配置

- `PUT /agents/{agent_code}/config`

请求体示例：

```json
{
  "model_name": "gpt-4.1",
  "temperature": 0.4,
  "max_tokens": 1500,
  "persona_desc": "诸葛孔明风格..."
}
```

### 3.8 上传知识文档

- `POST /knowledge/documents`

请求方式：

- `multipart/form-data`
- 或传入远程文件地址

请求体示例：

```json
{
  "corpus_name": "《四大名著》",
  "doc_title": "西游记全文",
  "file_url": "https://example.com/sanguo.txt"
}
```

响应体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "doc_id": "doc_0001",
    "parse_status": "pending"
  }
}
```

### 3.9 文档重建索引

- `POST /knowledge/documents/{doc_id}/reindex`

用途：

- 重新切片
- 重新生成向量
- 更新检索索引

### 3.10 知识检索

- `GET /knowledge/search?q=孙悟空&top_k=5`

响应体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "query": "孙悟空",
    "results": [
      {
        "chunk_id": "c_1024",
        "doc_title": "《西游记》",
        "score": 0.92,
        "excerpt": "..."
      }
    ]
  }
}
```

### 3.11 反馈提交

- `POST /feedback`

请求体：

```json
{
  "session_id": "s_202605060001",
  "message_id": "m_001",
  "rating": 5,
  "feedback_type": "like",
  "feedback_text": "回答很像孔明。"
}
```

### 3.12 健康检查

- `GET /health`

响应体：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok"
  }
}
```

## 4. 流式接口建议

若需实时输出回答，建议增加：

- `GET /sessions/{session_id}/messages/stream`

输出采用 SSE 事件：

- `token`
- `tool_call`
- `source`
- `done`

## 5. 接口字段说明

### 5.1 通用请求字段

| 字段名 | 类型 | 说明 |
|---|---|---|
| user_id | string | 用户标识 |
| content | string | 用户输入内容 |
| stream | boolean | 是否流式输出 |
| options | object | 额外参数 |

### 5.2 通用返回字段

| 字段名 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码 |
| message | string | 提示信息 |
| data | object | 业务数据 |

## 6. 安全与限制

1. 所有写接口建议鉴权。
2. 知识库上传接口建议限制文件类型和大小。
3. 会话消息接口建议做频控，防止刷接口。
4. 对敏感请求应返回可控拒答，不直接输出不安全内容。

