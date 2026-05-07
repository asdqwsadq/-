from __future__ import annotations

from fastapi import APIRouter

from app.schemas import ApiResponse, FeedbackCreateRequest
from app.services.session_service import session_service


router = APIRouter(tags=["反馈"])


@router.post("/反馈", response_model=ApiResponse)
@router.post("/feedback", response_model=ApiResponse)
def submit_feedback(payload: FeedbackCreateRequest) -> ApiResponse:
    record = session_service.record_feedback(payload.model_dump())
    return ApiResponse(data=record)
