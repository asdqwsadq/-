from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "成功"
    data: Any = None


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str | None = Field(default=None, alias="用户ID")
    title: str | None = Field(default=None, alias="标题")
    metadata: dict[str, Any] = Field(default_factory=dict, alias="元数据")


class SessionUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str | None = Field(default=None, alias="状态")
    title: str | None = Field(default=None, alias="标题")
    summary: str | None = Field(default=None, alias="摘要")


class MessageCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(alias="内容")
    stream: bool = Field(default=False, alias="流式")
    options: dict[str, Any] = Field(default_factory=dict, alias="选项")


class MessageRecord(BaseModel):
    message_id: str
    session_id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    source_type: str | None = None
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str


class SessionRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    agent_code: str
    user_id: str | None = None
    session_title: str | None = None
    summary: str | None = None
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
    last_message_at: str | None = None
    created_at: str
    updated_at: str


class AgentConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_name: str | None = Field(default=None, alias="模型名称")
    temperature: float | None = Field(default=None, alias="温度")
    max_tokens: int | None = Field(default=None, alias="最大令牌数")
    persona_desc: str | None = Field(default=None, alias="人设描述")
    rag_enabled: bool | None = Field(default=None, alias="RAG启用")


class KnowledgeUploadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    corpus_name: str = Field(alias="语料名称")
    doc_title: str = Field(alias="文档标题")
    file_url: str | None = Field(default=None, alias="文件URL")
    file_path: str | None = Field(default=None, alias="文件路径")


class FeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="会话ID")
    message_id: str | None = Field(default=None, alias="消息ID")
    rating: int = Field(ge=1, le=5, alias="评分")
    feedback_type: str | None = Field(default=None, alias="反馈类型")
    feedback_text: str | None = Field(default=None, alias="反馈内容")


class SearchQueryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(alias="问题")
    results: list[dict[str, Any]] = Field(alias="结果列表")


class PromptTemplateCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    template_code: str = Field(alias="模板编码")
    template_name: str = Field(alias="模板名称")
    template_type: str = Field(alias="模板类型")
    system_prompt: str = Field(alias="系统提示词")
    user_prompt: str | None = Field(default=None, alias="用户提示词")
    variables: dict[str, Any] = Field(default_factory=dict, alias="变量")
    version: str = Field(default="v1", alias="版本号")
    status: str = Field(default="active", alias="状态")


class PromptTemplateUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    template_name: str | None = Field(default=None, alias="模板名称")
    template_type: str | None = Field(default=None, alias="模板类型")
    system_prompt: str | None = Field(default=None, alias="系统提示词")
    user_prompt: str | None = Field(default=None, alias="用户提示词")
    variables: dict[str, Any] | None = Field(default=None, alias="变量")
    version: str | None = Field(default=None, alias="版本号")
    status: str | None = Field(default=None, alias="状态")


class PromptTemplateRecord(BaseModel):
    id: int
    template_code: str
    template_name: str
    template_type: str
    system_prompt: str
    user_prompt: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    version: str
    status: str
    created_at: str
    updated_at: str
