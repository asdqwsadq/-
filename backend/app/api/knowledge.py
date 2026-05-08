from __future__ import annotations

from datetime import datetime, timezone
from threading import Thread
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.kongming_agent.backend.app.core.config import settings
from app.kongming_agent.backend.app.schemas import ApiResponse, KnowledgeUploadRequest, SearchQueryResponse
from app.kongming_agent.backend.app.services.knowledge_base import FourClassicsKnowledgeBase
from app.kongming_agent.backend.app.services.knowledge_ingestion import ingestor
from app.kongming_agent.backend.app.services.session_service import session_service
from app.kongming_agent.backend.app.services.deepseek_client import deepseek_client


router = APIRouter(tags=["知识库"])
knowledge_base = FourClassicsKnowledgeBase()
_LAST_PROGRESS_SNAPSHOT: dict[str, tuple[int, str, str, int, int]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _log_progress(job_id: str, progress: dict[str, Any]) -> None:
    stage = str(progress.get("stage") or "running")
    message = str(progress.get("message") or "").strip()
    percent = float(progress.get("percent") or 0.0)
    current_percent = round(max(0.0, min(100.0, percent)), 1)
    stage_name_map = {
        "queued": "排队中",
        "preparing": "准备中",
        "chunking": "切片中",
        "planning_block": "切片中",
        "vectorizing": "向量化中",
        "persisting": "写库中",
        "document_completed": "单本文档完成",
        "finalizing": "收尾中",
        "completed": "已完成",
        "failed": "失败",
    }
    stage_label = stage_name_map.get(stage, stage)
    current_document = str(progress.get("current_document") or "-")
    current_done = int(progress.get("current_document_chunks_done") or 0)
    current_total = int(progress.get("current_document_chunks_total") or 0)
    current_percent_display = int(current_percent) if current_percent.is_integer() else current_percent
    snapshot = (
        int(current_percent * 10),
        stage_label,
        current_document,
        current_done,
        current_total,
    )
    last_snapshot = _LAST_PROGRESS_SNAPSHOT.get(job_id)
    if stage == "failed":
        message = str(progress.get("message") or "任务失败。")
        print(f"[knowledge_rebuild:{job_id}] 失败 | {message}", flush=True)
        return
    if stage == "completed":
        if last_snapshot != snapshot:
            print(f"[knowledge_rebuild:{job_id}] 进度 100% | 已完成", flush=True)
            _LAST_PROGRESS_SNAPSHOT[job_id] = snapshot
        return
    if last_snapshot == snapshot:
        return
    _LAST_PROGRESS_SNAPSHOT[job_id] = snapshot
    detail = ""
    if current_document != "-" and current_total > 0:
        detail = f" | {current_document} {current_done}/{current_total}"
    elif current_document != "-":
        detail = f" | {current_document}"
    elif message:
        detail = f" | {message}"
    print(
        f"[knowledge_rebuild:{job_id}] 进度 {current_percent_display}% | {stage_label}{detail}",
        flush=True,
    )


def _run_knowledge_rebuild(job_id: str) -> None:
    try:
        _LAST_PROGRESS_SNAPSHOT.pop(job_id, None)
        print(f"[knowledge_rebuild:{job_id}] 进度 0% | 准备中", flush=True)

        def progress_callback(progress: dict[str, Any]) -> None:
            session_service.update_job_progress(job_id, **progress)
            _log_progress(job_id, progress)

        result = knowledge_base.rebuild_vector_store(
            progress_callback=progress_callback
        )
        session_service.complete_job(job_id, result)
        _log_progress(job_id, {"stage": "completed", "percent": 100.0})
    except Exception as exc:
        session_service.fail_job(job_id, str(exc))
        _log_progress(job_id, {"stage": "failed", "message": str(exc)})
    finally:
        _LAST_PROGRESS_SNAPSHOT.pop(job_id, None)


@router.post("/知识库/文档", response_model=ApiResponse)
@router.post("/knowledge/documents", response_model=ApiResponse)
def upload_document(payload: KnowledgeUploadRequest) -> ApiResponse:
    record = session_service.register_document(
        {
            "corpus_name": payload.corpus_name,
            "doc_title": payload.doc_title,
            "file_url": payload.file_url,
            "file_path": payload.file_path,
            "parse_status": "pending",
        }
    )
    return ApiResponse(data=record)


@router.post("/知识库/文档/{doc_id}/重建", response_model=ApiResponse)
@router.post("/knowledge/documents/{doc_id}/reindex", response_model=ApiResponse)
def reindex_document(doc_id: str) -> ApiResponse:
    if doc_id not in {document["doc_id"] for document in session_service.list_documents()}:
        raise HTTPException(status_code=404, detail="文档未找到")
    knowledge_base.load()
    return ApiResponse(data={"doc_id": doc_id, "reindexed": True})


@router.post("/知识库/重建", response_model=ApiResponse)
@router.post("/knowledge/rebuild", response_model=ApiResponse)
def rebuild_knowledge_base() -> ApiResponse:
    running_job = session_service.find_running_job("knowledge_rebuild")
    if running_job:
        return ApiResponse(data=running_job)
    job = session_service.create_job(
        "knowledge_rebuild",
        payload={
            "mode": "full_rebuild",
            "vector_store": settings.milvus_collection,
            "chunk_model": settings.ollama_chunk_model,
            "embedding_model": settings.ollama_embedding_model,
        },
    )
    thread = Thread(target=_run_knowledge_rebuild, args=(job["job_id"],), daemon=True)
    thread.start()
    return ApiResponse(data=job)


@router.get("/知识库/重建/{job_id}", response_model=ApiResponse)
@router.get("/knowledge/rebuild/{job_id}", response_model=ApiResponse)
def get_rebuild_job(job_id: str) -> ApiResponse:
    job = session_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务未找到")
    return ApiResponse(data=job)


@router.get("/知识库/诊断", response_model=ApiResponse)
@router.get("/knowledge/diagnostics", response_model=ApiResponse)
def knowledge_diagnostics() -> ApiResponse:
    preflight = ingestor.preflight_check()
    preflight["deepseek"] = deepseek_client.preflight()
    return ApiResponse(data=preflight)


@router.get("/知识库/检索", response_model=ApiResponse)
@router.get("/knowledge/search", response_model=ApiResponse)
def search_knowledge(q: str = Query(alias="问题"), top_k: int = Query(default=5, ge=1, le=20, alias="数量")) -> ApiResponse:
    results = knowledge_base.search(q, top_k=top_k)
    return ApiResponse(data=SearchQueryResponse(query=q, results=results).model_dump())
