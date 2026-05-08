from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import NoResultFound

from app.kongming_agent.backend.app.core.config import settings
from app.kongming_agent.backend.app.core.database import inspect_database, session_scope
from app.kongming_agent.backend.app.models.mysql import (
    AgentProfile,
    AppMeta,
    ChatSession,
    Feedback,
    Job,
    KnowledgeDocument,
    Message,
    PromptTemplate,
    RetrievalLog,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _deepcopy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(payload)


class SessionService:
    def ensure_agent_profile(self, agent_code: str) -> dict[str, Any]:
        with session_scope() as db:
            profile = db.get(AgentProfile, agent_code)
            if profile is None:
                profile = AgentProfile(
                    agent_code=agent_code,
                    agent_name="诸葛孔明 Agent",
                    persona_name="诸葛孔明",
                    persona_desc="以诸葛孔明人格进行四大名著知识问答与延伸分析。",
                    model_name=settings.default_model_name,
                    temperature=settings.default_temperature,
                    max_tokens=settings.default_max_tokens,
                    rag_enabled=True,
                    status="active",
                    created_at=_now(),
                    updated_at=_now(),
                )
                db.add(profile)
            return self._agent_to_dict(profile)

    def create_session(
        self,
        agent_code: str,
        user_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.ensure_agent_profile(agent_code)
        session_id = self.next_id("session")
        now = _now()
        record = ChatSession(
            session_id=session_id,
            agent_code=agent_code,
            user_id=user_id,
            session_title=title,
            summary="",
            status="active",
            metadata_json=metadata or {},
            last_message_at=None,
            created_at=now,
            updated_at=now,
        )
        with session_scope() as db:
            db.add(record)
        return self._session_to_dict(record)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with session_scope() as db:
            record = db.get(ChatSession, session_id)
            return self._session_to_dict(record) if record else None

    def update_session(self, session_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        with session_scope() as db:
            record = db.get(ChatSession, session_id)
            if record is None:
                return None
            for key in ("status", "title", "summary"):
                if key in patch and patch[key] is not None:
                    if key == "title":
                        record.session_title = patch[key]
                    else:
                        setattr(record, key, patch[key])
            record.updated_at = _now()
            db.add(record)
            return self._session_to_dict(record)

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        with session_scope() as db:
            rows = db.scalars(
                select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
            ).all()
            return [self._message_to_dict(row) for row in rows]

    def list_sessions(self) -> list[dict[str, Any]]:
        with session_scope() as db:
            rows = db.scalars(select(ChatSession).order_by(ChatSession.created_at.desc())).all()
            return [self._session_to_dict(row) for row in rows]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        source_type: str | None = None,
        source_refs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        message_id = self.next_id("message")
        now = _now()
        record = Message(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            source_type=source_type,
            source_refs_json=source_refs or [],
            created_at=now,
        )
        with session_scope() as db:
            db.add(record)
            session = db.get(ChatSession, session_id)
            if session:
                session.last_message_at = now
                session.updated_at = now
        return self._message_to_dict(record)

    def update_summary(self, session_id: str, summary: str) -> None:
        with session_scope() as db:
            session = db.get(ChatSession, session_id)
            if session:
                session.summary = summary
                session.updated_at = _now()

    def update_agent_config(self, agent_code: str, patch: dict[str, Any]) -> dict[str, Any]:
        profile = self.ensure_agent_profile(agent_code)
        with session_scope() as db:
            record = db.get(AgentProfile, agent_code)
            if record is None:
                raise RuntimeError("agent profile missing")
            for key, value in patch.items():
                if value is not None and hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = _now()
            db.add(record)
            return self._agent_to_dict(record)

    def get_agent_config(self, agent_code: str) -> dict[str, Any]:
        return self.ensure_agent_profile(agent_code)

    def record_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        feedback_id = self.next_id("feedback")
        record = Feedback(
            feedback_id=feedback_id,
            session_id=payload["session_id"],
            message_id=payload.get("message_id"),
            rating=payload["rating"],
            feedback_type=payload.get("feedback_type"),
            feedback_text=payload.get("feedback_text"),
            created_at=_now(),
        )
        with session_scope() as db:
            db.add(record)
        return self._feedback_to_dict(record)

    def register_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        doc_id = payload.get("doc_id") or self.next_id("doc")
        now = _now()
        with session_scope() as db:
            record = db.get(KnowledgeDocument, doc_id)
            if record is None:
                record = KnowledgeDocument(
                    doc_id=doc_id,
                    corpus_name=payload["corpus_name"],
                    doc_title=payload["doc_title"],
                    file_url=payload.get("file_url"),
                    file_path=payload.get("file_path"),
                    parse_status=payload.get("parse_status", "pending"),
                    created_at=now,
                    updated_at=now,
                )
                db.add(record)
            else:
                record.corpus_name = payload["corpus_name"]
                record.doc_title = payload["doc_title"]
                record.file_url = payload.get("file_url")
                record.file_path = payload.get("file_path")
                record.parse_status = payload.get("parse_status", "pending")
                record.updated_at = now
            return self._document_to_dict(record)

    def list_documents(self) -> list[dict[str, Any]]:
        with session_scope() as db:
            rows = db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())).all()
            return [self._document_to_dict(row) for row in rows]

    def record_retrieval(
        self,
        session_id: str,
        query_text: str,
        top_k: int,
        retrieved_chunks: list[dict[str, Any]],
        latency_ms: int,
    ) -> None:
        record = RetrievalLog(
            log_id=self.next_id("log"),
            session_id=session_id,
            query_text=query_text,
            top_k=top_k,
            retrieved_chunks_json=retrieved_chunks,
            latency_ms=latency_ms,
            created_at=_now(),
        )
        with session_scope() as db:
            db.add(record)

    def create_job(self, job_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        job_id = self.next_id("job")
        now = _now()
        record = Job(
            job_id=job_id,
            job_type=job_type,
            status="running",
            payload_json=payload or {},
            progress_json={
                "stage": "queued",
                "message": "任务已创建，等待启动。",
                "processed_documents": 0,
                "total_documents": 0,
                "current_document": None,
                "current_document_chunks_done": 0,
                "current_document_chunks_total": 0,
                "vectorized_chunks": 0,
                "persisted_chunks": 0,
                "percent": 0.0,
            },
            result_json=None,
            error=None,
            created_at=now,
            updated_at=now,
            started_at=now,
            finished_at=None,
        )
        with session_scope() as db:
            db.add(record)
        return self._job_to_dict(record)

    def find_running_job(self, job_type: str) -> dict[str, Any] | None:
        with session_scope() as db:
            row = db.scalars(
                select(Job)
                .where(Job.job_type == job_type, Job.status == "running")
                .order_by(Job.created_at.desc())
                .limit(1)
            ).first()
            return self._job_to_dict(row) if row else None

    def update_job_progress(self, job_id: str, **progress_patch: Any) -> dict[str, Any] | None:
        with session_scope() as db:
            job = db.get(Job, job_id)
            if job is None:
                return None
            progress = dict(job.progress_json or {})
            for key, value in progress_patch.items():
                if value is not None:
                    progress[key] = value
            job.progress_json = progress
            job.progress_json["percent"] = self._compute_percent(job.progress_json)
            job.updated_at = _now()
            db.add(job)
            return self._job_to_dict(job)

    def complete_job(self, job_id: str, result: dict[str, Any] | None = None) -> dict[str, Any] | None:
        with session_scope() as db:
            job = db.get(Job, job_id)
            if job is None:
                return None
            progress = dict(job.progress_json or {})
            progress.update(
                {
                    "stage": "completed",
                    "message": "全量灌库完成。",
                    "percent": 100.0,
                    "current_document": None,
                    "current_document_chunks_done": progress.get("current_document_chunks_total", 0),
                }
            )
            job.progress_json = progress
            job.status = "completed"
            job.result_json = result or {}
            job.finished_at = _now()
            job.updated_at = job.finished_at
            db.add(job)
            return self._job_to_dict(job)

    def fail_job(self, job_id: str, error: str) -> dict[str, Any] | None:
        with session_scope() as db:
            job = db.get(Job, job_id)
            if job is None:
                return None
            progress = dict(job.progress_json or {})
            progress.update(
                {
                    "stage": "failed",
                    "message": error,
                }
            )
            job.progress_json = progress
            job.status = "failed"
            job.error = error
            job.finished_at = _now()
            job.updated_at = job.finished_at
            db.add(job)
            return self._job_to_dict(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with session_scope() as db:
            job = db.get(Job, job_id)
            return self._job_to_dict(job) if job else None

    def stats(self) -> dict[str, Any]:
        with session_scope() as db:
            agent_count = db.scalar(select(func.count()).select_from(AgentProfile)) or 0
            session_count = db.scalar(select(func.count()).select_from(ChatSession)) or 0
            message_count = db.scalar(select(func.count()).select_from(Message)) or 0
            document_count = db.scalar(select(func.count()).select_from(KnowledgeDocument)) or 0
            prompt_template_count = db.scalar(select(func.count()).select_from(PromptTemplate)) or 0
            feedback_count = db.scalar(select(func.count()).select_from(Feedback)) or 0
            retrieval_count = db.scalar(select(func.count()).select_from(RetrievalLog)) or 0
            job_count = db.scalar(select(func.count()).select_from(Job)) or 0
            running_job_count = db.scalar(select(func.count()).select_from(Job).where(Job.status == "running")) or 0
            return {
                "agent_count": agent_count,
                "session_count": session_count,
                "message_count": message_count,
                "document_count": document_count,
                "prompt_template_count": prompt_template_count,
                "feedback_count": feedback_count,
                "retrieval_count": retrieval_count,
                "job_count": job_count,
                "running_job_count": running_job_count,
                "last_updated_at": _iso(_now()),
            }

    def database_status(self) -> dict[str, Any]:
        with session_scope() as db:
            stats = {
                "agent_profiles": db.scalar(select(func.count()).select_from(AgentProfile)) or 0,
                "sessions": db.scalar(select(func.count()).select_from(ChatSession)) or 0,
                "messages": db.scalar(select(func.count()).select_from(Message)) or 0,
                "documents": db.scalar(select(func.count()).select_from(KnowledgeDocument)) or 0,
                "prompt_templates": db.scalar(select(func.count()).select_from(PromptTemplate)) or 0,
                "feedback": db.scalar(select(func.count()).select_from(Feedback)) or 0,
                "retrieval_logs": db.scalar(select(func.count()).select_from(RetrievalLog)) or 0,
                "jobs": db.scalar(select(func.count()).select_from(Job)) or 0,
            }
        database_info = inspect_database()
        return {
            "connected": True,
            "database": database_info,
            "counts": stats,
            "last_checked_at": _iso(_now()),
        }

    def next_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def list_prompt_templates(self) -> list[dict[str, Any]]:
        with session_scope() as db:
            rows = db.scalars(select(PromptTemplate).order_by(PromptTemplate.created_at.desc())).all()
            return [self._prompt_template_to_dict(row) for row in rows]

    def get_prompt_template(self, template_code: str) -> dict[str, Any] | None:
        with session_scope() as db:
            row = db.scalars(select(PromptTemplate).where(PromptTemplate.template_code == template_code)).first()
            return self._prompt_template_to_dict(row) if row else None

    def create_prompt_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        with session_scope() as db:
            exists = db.scalars(select(PromptTemplate).where(PromptTemplate.template_code == payload["template_code"])).first()
            if exists:
                raise ValueError("template_code already exists")
            row = PromptTemplate(
                template_code=payload["template_code"],
                template_name=payload["template_name"],
                template_type=payload["template_type"],
                system_prompt=payload["system_prompt"],
                user_prompt=payload.get("user_prompt"),
                variables_json=payload.get("variables") or {},
                version=payload.get("version", "v1"),
                status=payload.get("status", "active"),
                created_at=_now(),
                updated_at=_now(),
            )
            db.add(row)
            db.flush()
            return self._prompt_template_to_dict(row)

    def update_prompt_template(self, template_code: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        with session_scope() as db:
            row = db.scalars(select(PromptTemplate).where(PromptTemplate.template_code == template_code)).first()
            if row is None:
                return None
            for key, value in patch.items():
                if value is None:
                    continue
                if key == "template_name":
                    row.template_name = value
                elif key == "template_type":
                    row.template_type = value
                elif key == "system_prompt":
                    row.system_prompt = value
                elif key == "user_prompt":
                    row.user_prompt = value
                elif key == "variables":
                    row.variables_json = value
                elif key == "version":
                    row.version = value
                elif key == "status":
                    row.status = value
            row.updated_at = _now()
            db.add(row)
            return self._prompt_template_to_dict(row)

    def delete_prompt_template(self, template_code: str) -> bool:
        with session_scope() as db:
            row = db.scalars(select(PromptTemplate).where(PromptTemplate.template_code == template_code)).first()
            if row is None:
                return False
            db.delete(row)
            return True

    def _compute_percent(self, progress: dict[str, Any]) -> float:
        total_documents = int(progress.get("total_documents") or 0)
        processed_documents = int(progress.get("processed_documents") or 0)
        current_done = int(progress.get("current_document_chunks_done") or 0)
        current_total = int(progress.get("current_document_chunks_total") or 0)
        stage = str(progress.get("stage") or "")
        if total_documents <= 0:
            return float(progress.get("percent") or 0.0)

        stage_weights = {
            "chunking": (0.00, 0.05),
            "planning_block": (0.05, 0.20),
            "vectorizing": (0.20, 0.90),
            "persisting": (0.90, 0.98),
            "document_completed": (1.00, 1.00),
            "finalizing": (0.99, 1.00),
            "completed": (1.00, 1.00),
        }
        start_weight, end_weight = stage_weights.get(stage, (0.0, 0.0))
        stage_fraction = 0.0
        if current_total > 0:
            stage_fraction = min(1.0, current_done / current_total)
        document_fraction = start_weight + ((end_weight - start_weight) * stage_fraction)
        if stage in {"document_completed", "completed"}:
            document_fraction = 1.0
        percent = ((processed_documents + document_fraction) / total_documents) * 100.0
        return round(min(100.0, max(0.0, percent)), 2)

    def _agent_to_dict(self, row: AgentProfile | None) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "agent_code": row.agent_code,
            "agent_name": row.agent_name,
            "persona_name": row.persona_name,
            "persona_desc": row.persona_desc,
            "model_name": row.model_name,
            "temperature": row.temperature,
            "max_tokens": row.max_tokens,
            "rag_enabled": row.rag_enabled,
            "status": row.status,
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }

    def _session_to_dict(self, row: ChatSession | None) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "session_id": row.session_id,
            "agent_code": row.agent_code,
            "user_id": row.user_id,
            "session_title": row.session_title,
            "summary": row.summary,
            "status": row.status,
            "metadata": row.metadata_json or {},
            "last_message_at": _iso(row.last_message_at),
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }

    def _message_to_dict(self, row: Message | None) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "message_id": row.message_id,
            "session_id": row.session_id,
            "role": row.role,
            "content": row.content,
            "source_type": row.source_type,
            "source_refs": row.source_refs_json or [],
            "created_at": _iso(row.created_at),
        }

    def _feedback_to_dict(self, row: Feedback | None) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "feedback_id": row.feedback_id,
            "session_id": row.session_id,
            "message_id": row.message_id,
            "rating": row.rating,
            "feedback_type": row.feedback_type,
            "feedback_text": row.feedback_text,
            "created_at": _iso(row.created_at),
        }

    def _document_to_dict(self, row: KnowledgeDocument | None) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "doc_id": row.doc_id,
            "corpus_name": row.corpus_name,
            "doc_title": row.doc_title,
            "file_url": row.file_url,
            "file_path": row.file_path,
            "parse_status": row.parse_status,
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }

    def _job_to_dict(self, row: Job | None) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "job_id": row.job_id,
            "job_type": row.job_type,
            "status": row.status,
            "payload": row.payload_json or {},
            "progress": row.progress_json or {},
            "result": row.result_json or {},
            "error": row.error,
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
            "started_at": _iso(row.started_at),
            "finished_at": _iso(row.finished_at),
        }

    def _prompt_template_to_dict(self, row: PromptTemplate | None) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "id": row.id,
            "template_code": row.template_code,
            "template_name": row.template_name,
            "template_type": row.template_type,
            "system_prompt": row.system_prompt,
            "user_prompt": row.user_prompt,
            "variables": row.variables_json or {},
            "version": row.version,
            "status": row.status,
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }


session_service = SessionService()
