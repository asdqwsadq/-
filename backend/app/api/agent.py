from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas import AgentConfigUpdateRequest, ApiResponse, MessageCreateRequest, SessionCreateRequest, SessionRecord, SessionUpdateRequest
from app.services.kongming_agent import kongming_agent_service
from app.services.session_service import session_service


router = APIRouter(tags=["会话与智能体"])


@router.post("/智能体/{agent_code}/会话", response_model=ApiResponse)
@router.post("/agents/{agent_code}/sessions", response_model=ApiResponse)
def create_session(agent_code: str, payload: SessionCreateRequest) -> ApiResponse:
    session = session_service.create_session(agent_code, payload.user_id, payload.title, payload.metadata)
    return ApiResponse(data=session)


@router.get("/会话/{session_id}", response_model=ApiResponse)
@router.get("/sessions/{session_id}", response_model=ApiResponse)
def get_session(session_id: str) -> ApiResponse:
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话未找到")
    return ApiResponse(data=SessionRecord(**session).model_dump())


@router.patch("/会话/{session_id}", response_model=ApiResponse)
@router.patch("/sessions/{session_id}", response_model=ApiResponse)
def patch_session(session_id: str, payload: SessionUpdateRequest) -> ApiResponse:
    session = session_service.update_session(session_id, payload.model_dump())
    if not session:
        raise HTTPException(status_code=404, detail="会话未找到")
    return ApiResponse(data=session)


@router.get("/会话/{session_id}/消息", response_model=ApiResponse)
@router.get("/sessions/{session_id}/messages", response_model=ApiResponse)
def list_messages(session_id: str, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)) -> ApiResponse:
    messages = session_service.list_messages(session_id)
    start = (page - 1) * page_size
    end = start + page_size
    return ApiResponse(data={"session_id": session_id, "items": messages[start:end], "total": len(messages)})


@router.post("/会话/{session_id}/消息", response_model=ApiResponse)
@router.post("/sessions/{session_id}/messages", response_model=ApiResponse)
def send_message(session_id: str, payload: MessageCreateRequest):
    if not session_service.get_session(session_id):
        raise HTTPException(status_code=404, detail="会话未找到")

    if payload.stream:
        def generate():
            for event_type, data in kongming_agent_service.answer_stream(
                session_id=session_id,
                question=payload.content,
                top_k=payload.options.get("top_k"),
                use_rag=payload.options.get("use_rag", True),
            ):
                yield f"data: {json.dumps({'type': event_type, 'payload': data}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    result = kongming_agent_service.answer(
        session_id=session_id,
        question=payload.content,
        top_k=payload.options.get("top_k"),
        use_rag=payload.options.get("use_rag", True),
    )
    return ApiResponse(
        data={
            "session_id": session_id,
            "answer": result.answer,
            "sources": result.sources,
            "usage": result.usage,
        }
    )


@router.get("/智能体/{agent_code}/配置", response_model=ApiResponse)
@router.get("/agents/{agent_code}/config", response_model=ApiResponse)
def get_agent_config(agent_code: str) -> ApiResponse:
    return ApiResponse(data=session_service.get_agent_config(agent_code))


@router.put("/智能体/{agent_code}/配置", response_model=ApiResponse)
@router.put("/agents/{agent_code}/config", response_model=ApiResponse)
def update_agent_config(agent_code: str, payload: AgentConfigUpdateRequest) -> ApiResponse:
    config = session_service.update_agent_config(agent_code, payload.model_dump(exclude_none=True))
    return ApiResponse(data=config)
