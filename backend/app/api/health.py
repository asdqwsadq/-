from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas import ApiResponse


router = APIRouter(tags=["健康检查"])


@router.get("/健康", response_model=ApiResponse)
@router.get("/health", response_model=ApiResponse)
def health() -> ApiResponse:
    return ApiResponse(data={"status": "ok", "service": settings.app_name, "version": settings.app_version})
