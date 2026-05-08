from __future__ import annotations

from fastapi import APIRouter

from app.kongming_agent.backend.app.core.config import settings
from app.kongming_agent.backend.app.schemas import ApiResponse


router = APIRouter(tags=["健康检查"])


@router.get("/健康", response_model=ApiResponse)
@router.get("/health", response_model=ApiResponse)
def health() -> ApiResponse:
    return ApiResponse(data={"status": "ok", "service": settings.app_name, "version": settings.app_version})
