from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import ApiResponse
from app.services.session_service import session_service
from app.schemas import PromptTemplateCreateRequest, PromptTemplateUpdateRequest


router = APIRouter(tags=["管理"])


@router.get("/管理/概览", response_model=ApiResponse)
@router.get("/admin/overview", response_model=ApiResponse)
def admin_overview() -> ApiResponse:
    return ApiResponse(data=session_service.stats())


@router.get("/管理/数据库", response_model=ApiResponse)
@router.get("/admin/database", response_model=ApiResponse)
def admin_database() -> ApiResponse:
    return ApiResponse(data=session_service.database_status())


@router.get("/管理/会话", response_model=ApiResponse)
@router.get("/admin/sessions", response_model=ApiResponse)
def admin_sessions() -> ApiResponse:
    sessions = session_service.list_sessions()
    return ApiResponse(data={"items": sessions, "total": len(sessions)})


@router.get("/管理/文档", response_model=ApiResponse)
@router.get("/admin/documents", response_model=ApiResponse)
def admin_documents() -> ApiResponse:
    documents = session_service.list_documents()
    return ApiResponse(data={"items": documents, "total": len(documents)})


@router.get("/管理/模板", response_model=ApiResponse)
@router.get("/admin/prompt-templates", response_model=ApiResponse)
def admin_prompt_templates() -> ApiResponse:
    templates = session_service.list_prompt_templates()
    return ApiResponse(data={"items": templates, "total": len(templates)})


@router.post("/管理/模板", response_model=ApiResponse)
@router.post("/admin/prompt-templates", response_model=ApiResponse)
def create_prompt_template(payload: PromptTemplateCreateRequest) -> ApiResponse:
    try:
        template = session_service.create_prompt_template(payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApiResponse(data=template)


@router.get("/管理/模板/{template_code}", response_model=ApiResponse)
@router.get("/admin/prompt-templates/{template_code}", response_model=ApiResponse)
def get_prompt_template(template_code: str) -> ApiResponse:
    template = session_service.get_prompt_template(template_code)
    if not template:
        raise HTTPException(status_code=404, detail="模板未找到")
    return ApiResponse(data=template)


@router.put("/管理/模板/{template_code}", response_model=ApiResponse)
@router.put("/admin/prompt-templates/{template_code}", response_model=ApiResponse)
def update_prompt_template(template_code: str, payload: PromptTemplateUpdateRequest) -> ApiResponse:
    template = session_service.update_prompt_template(template_code, payload.model_dump(exclude_none=True))
    if not template:
        raise HTTPException(status_code=404, detail="模板未找到")
    return ApiResponse(data=template)


@router.delete("/管理/模板/{template_code}", response_model=ApiResponse)
@router.delete("/admin/prompt-templates/{template_code}", response_model=ApiResponse)
def delete_prompt_template(template_code: str) -> ApiResponse:
    deleted = session_service.delete_prompt_template(template_code)
    if not deleted:
        raise HTTPException(status_code=404, detail="模板未找到")
    return ApiResponse(data={"template_code": template_code, "deleted": True})
