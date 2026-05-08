from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.kongming_agent.backend.app.core.config import settings
from app.kongming_agent.backend.app.services.milvus_store import MilvusChunkRecord, get_milvus_store
from app.kongming_agent.backend.app.services.ollama_client import ollama_client


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass
class ChunkPlan:
    chunk_id: str
    doc_title: str
    corpus_name: str
    chunk_text: str
    metadata: dict[str, Any]


class FourClassicsIngestor:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or settings.project_root
        self.milvus = get_milvus_store()

    def load_documents(self) -> list[tuple[str, str, str]]:
        docs: list[tuple[str, str, str]] = []
        for file_path in sorted(self.project_root.glob("*.txt")):
            docs.append((file_path.stem, file_path.name, file_path.read_text(encoding="utf-8", errors="ignore")))
        return docs

    def preflight_check(self) -> dict[str, Any]:
        docs = self.load_documents()
        try:
            ollama_status = ollama_client.preflight(settings.ollama_chunk_model)
        except Exception as exc:
            ollama_status = {
                "ollama_reachable": False,
                "chunk_model": settings.ollama_chunk_model,
                "chunk_model_present": False,
                "error": str(exc),
            }
        try:
            raw = ollama_client.preflight(settings.ollama_embedding_model)
            embedding_status = {
                "reachable": raw.get("ollama_reachable", False),
                "available_models": raw.get("available_models", []),
                "model": settings.ollama_embedding_model,
                "dimension": settings.embedding_dim,
                "latency_ms": raw.get("latency_ms"),
                "error": raw.get("error"),
            }
            embedding_status["embedding_model_present"] = (
                settings.ollama_embedding_model in embedding_status["available_models"]
            )
        except Exception as exc:
            embedding_status = {
                "reachable": False,
                "base_url": settings.ollama_base_url,
                "model": settings.ollama_embedding_model,
                "dimension": settings.embedding_dim,
                "latency_ms": None,
                "error": str(exc),
            }
        milvus_ok = False
        milvus_error: str | None = None
        try:
            self.milvus.connect()
            milvus_ok = True
        except Exception as exc:
            milvus_error = str(exc)
        return {
            "document_count": len(docs),
            "documents": [doc_title for _, doc_title, _ in docs],
            "chunk_strategy": "llm" if settings.use_llm_chunk_planning else "heuristic-fast",
            "chunk_model": settings.ollama_chunk_model,
            "embedding_model": settings.ollama_embedding_model,
            "embedding_workers": settings.embedding_workers,
            "embedding_batch_size": settings.dashscope_embedding_batch_size,
            "chunk_target_size": settings.chunk_target_size,
            "chunk_max_size": settings.chunk_max_size,
            "embedding_dim": settings.embedding_dim,
            "ollama": ollama_status,
            "embedding": embedding_status,
            "milvus": {
                "reachable": milvus_ok,
                "host": settings.milvus_host,
                "port": settings.milvus_port,
                "collection": settings.milvus_collection,
                "error": milvus_error,
            },
        }

    def split_document(
        self,
        corpus_name: str,
        doc_title: str,
        text: str,
        total_documents: int = 0,
        processed_documents: int = 0,
        progress_callback: ProgressCallback | None = None,
    ) -> list[ChunkPlan]:
        text = _normalize(text)
        if not text:
            return []

        blocks = self._chapter_blocks(text)
        chunks: list[ChunkPlan] = []
        index = 1
        total_blocks = len(blocks)
        for block_index, block in enumerate(blocks, start=1):
            self._emit_progress(
                progress_callback,
                stage="planning_block",
                message=f"正在规划 {doc_title} 第 {block_index}/{total_blocks} 个块",
                total_documents=total_documents,
                processed_documents=processed_documents,
                current_document=doc_title,
                current_document_chunks_done=block_index - 1,
                current_document_chunks_total=total_blocks,
            )
            planned = self._plan_block_with_qwen(corpus_name, doc_title, block, block_index)
            self._emit_progress(
                progress_callback,
                stage="planning_block",
                message=f"已规划 {doc_title} 第 {block_index}/{total_blocks} 个块",
                total_documents=total_documents,
                processed_documents=processed_documents,
                current_document=doc_title,
                current_document_chunks_done=block_index,
                current_document_chunks_total=total_blocks,
            )
            for item in planned:
                chunk_text = item.get("text", "").strip()
                if not chunk_text:
                    continue
                chunks.append(
                    ChunkPlan(
                        chunk_id=f"{corpus_name}_{index:05d}",
                        doc_title=doc_title,
                        corpus_name=corpus_name,
                        chunk_text=chunk_text[: settings.chunk_max_size],
                        metadata={
                            "block_index": block_index,
                            "chunk_index": index,
                            "source": item.get("source", "qwen2.5:14b"),
                            "title_hint": item.get("title", ""),
                        },
                    )
                )
                index += 1
        return chunks

    def ingest_all(self, force: bool = False, progress_callback: ProgressCallback | None = None, batch_size: int | None = None) -> dict[str, Any]:
        docs = self.load_documents()
        total_documents = len(docs)
        vectorized_chunks = 0
        persisted_chunks = 0
        embedding_batch_size = max(
            1,
            batch_size or settings.dashscope_embedding_batch_size,
        )

        self._emit_progress(
            progress_callback,
            stage="preparing",
            message="开始准备全量灌库。",
            total_documents=total_documents,
            processed_documents=0,
            current_document=None,
            current_document_chunks_done=0,
            current_document_chunks_total=0,
            vectorized_chunks=0,
            persisted_chunks=0,
        )
        preflight = self.preflight_check()
        self._emit_progress(
            progress_callback,
            stage="preparing",
            message=(
                "预检完成："
                f" docs={preflight['document_count']},"
                f" chunk={preflight['chunk_strategy']},"
                f" embedding={preflight['embedding_model']},"
                f" dim={preflight['embedding']['dimension']},"
                f" workers={preflight['embedding_workers']}"
            ),
            total_documents=total_documents,
            processed_documents=0,
        )
        if not preflight["ollama"]["chunk_model_present"]:
            raise RuntimeError(f"切片模型 {settings.ollama_chunk_model} 不可用。")
        if not preflight["embedding"]["reachable"]:
            raise RuntimeError(f"Ollama 嵌入模型预检失败：{preflight['embedding']}")
        if not preflight["embedding"].get("embedding_model_present"):
            raise RuntimeError(f"Ollama 嵌入模型 {settings.ollama_embedding_model} 不可用。")
        if not preflight["milvus"]["reachable"]:
            raise RuntimeError(
                f"Milvus 不可连接：{preflight['milvus']['error'] or 'unknown error'}"
            )
        if force:
            self._emit_progress(
                progress_callback,
                stage="preparing",
                message="正在清理旧的 Milvus collection。",
                total_documents=total_documents,
            )
            self.milvus.drop_collection()
        ingested_docs: list[str] = []
        pending_records: list[MilvusChunkRecord] = []
        for doc_index, (corpus_name, doc_title, text) in enumerate(docs, start=1):
            self._emit_progress(
                progress_callback,
                stage="chunking",
                message=f"正在切片 {doc_title}",
                total_documents=total_documents,
                processed_documents=doc_index - 1,
                current_document=doc_title,
                current_document_chunks_done=0,
                current_document_chunks_total=0,
                vectorized_chunks=vectorized_chunks,
                persisted_chunks=persisted_chunks,
            )
            plans = self.split_document(
                corpus_name,
                doc_title,
                text,
                total_documents=total_documents,
                processed_documents=doc_index - 1,
                progress_callback=progress_callback,
            )
            current_total = len(plans)
            if not plans:
                continue

            self._emit_progress(
                progress_callback,
                stage="vectorizing",
                message=f"正在向量化 {doc_title}",
                total_documents=total_documents,
                processed_documents=doc_index - 1,
                current_document=doc_title,
                current_document_chunks_done=0,
                current_document_chunks_total=current_total,
                vectorized_chunks=vectorized_chunks,
                persisted_chunks=persisted_chunks,
            )
            current_done = 0
            self._emit_progress(
                progress_callback,
                stage="vectorizing",
                message=f"正在批量向量化 {doc_title}，批大小 {embedding_batch_size}",
                total_documents=total_documents,
                processed_documents=doc_index - 1,
                current_document=doc_title,
                current_document_chunks_done=0,
                current_document_chunks_total=current_total,
                vectorized_chunks=vectorized_chunks,
                persisted_chunks=persisted_chunks,
            )

            for start in range(0, len(plans), embedding_batch_size):
                plan_batch = plans[start : start + embedding_batch_size]
                vectors = self.embed_chunks([plan.chunk_text for plan in plan_batch])
                for plan, vector in zip(plan_batch, vectors):
                    vectorized_chunks += 1
                    current_done += 1
                    pending_records.append(
                        MilvusChunkRecord(
                            chunk_id=plan.chunk_id,
                            corpus_name=plan.corpus_name,
                            doc_title=plan.doc_title,
                            chunk_text=plan.chunk_text,
                            metadata=plan.metadata,
                            vector=vector,
                        )
                    )

                self._emit_progress(
                    progress_callback,
                    stage="vectorizing",
                    message=f"正在批量向量化 {doc_title}",
                    total_documents=total_documents,
                    processed_documents=doc_index - 1,
                    current_document=doc_title,
                    current_document_chunks_done=current_done,
                    current_document_chunks_total=current_total,
                    vectorized_chunks=vectorized_chunks,
                    persisted_chunks=persisted_chunks,
                )

            ingested_docs.append(doc_title)
            self._emit_progress(
                progress_callback,
                stage="document_completed",
                message=f"{doc_title} 已完成向量化，等待统一写入。",
                total_documents=total_documents,
                processed_documents=doc_index,
                current_document=doc_title,
                current_document_chunks_done=current_total,
                current_document_chunks_total=current_total,
                vectorized_chunks=vectorized_chunks,
                persisted_chunks=persisted_chunks,
            )

        if pending_records:
            self._emit_progress(
                progress_callback,
                stage="persisting",
                message=f"正在一次性写入 Milvus，共 {len(pending_records)} 条向量。",
                total_documents=total_documents,
                processed_documents=total_documents,
                current_document=None,
                current_document_chunks_done=0,
                current_document_chunks_total=0,
                vectorized_chunks=vectorized_chunks,
                persisted_chunks=0,
            )
            self.milvus.upsert(pending_records)
            persisted_chunks = len(pending_records)
        else:
            persisted_chunks = 0
        self._emit_progress(
            progress_callback,
            stage="finalizing",
            message="所有知识文档均已写入 Milvus。",
            total_documents=total_documents,
            processed_documents=total_documents,
            current_document=None,
            current_document_chunks_done=0,
            current_document_chunks_total=0,
            vectorized_chunks=vectorized_chunks,
            persisted_chunks=persisted_chunks,
        )
        return {
            "documents": ingested_docs,
            "document_count": len(ingested_docs),
            "chunks": persisted_chunks,
            "vectorized_chunks": vectorized_chunks,
            "collection": settings.milvus_collection,
            "force": force,
        }

    def embed_text(self, text: str) -> list[float]:
        try:
            return ollama_client.embed(
                settings.ollama_embedding_model,
                text,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Ollama 嵌入模型 {settings.ollama_embedding_model} 不可用，未能生成真实向量。"
            ) from exc

    def embed_chunks(self, texts: list[str]) -> list[list[float]]:
        try:
            return ollama_client.embed_batch(
                settings.ollama_embedding_model,
                texts,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Ollama 嵌入模型 {settings.ollama_embedding_model} 批量向量化失败。"
            ) from exc

    def embed_chunk(self, text: str) -> list[float]:
        return self.embed_text(text)

    def embed_query(self, text: str) -> list[float]:
        return self.embed_text(text)

    def _plan_block_with_qwen(self, corpus_name: str, doc_title: str, block: str, block_index: int) -> list[dict[str, Any]]:
        if not settings.use_llm_chunk_planning:
            return self._fast_blocks(block)
        block = block[:12000]
        system = (
            "你是中文知识库切片器。你的任务是将文本切成适合向量检索的知识片段。"
            f"每片段建议 {settings.chunk_target_size} 到 {settings.chunk_max_size} 字之间。"
            "请尽量保持同一情节或同一回合的内容在一个片段内。"
            '输出必须是 JSON 对象，格式为 {"chunks":[{"title":"...","text":"..."}] }。'
            "不要输出解释，不要输出多余字段。"
        )
        user = (
            f"语料名称：{corpus_name}\n"
            f"文档标题：{doc_title}\n"
            f"块序号：{block_index}\n"
            f"文本：\n{block}"
        )
        try:
            payload = ollama_client.json_chat(settings.ollama_chunk_model, system, user, temperature=0.15)
            chunks = payload.get("chunks") if isinstance(payload, dict) else None
            if isinstance(chunks, list) and chunks:
                normalized: list[dict[str, Any]] = []
                for item in chunks:
                    if isinstance(item, dict):
                        normalized.append(
                            {
                                "title": item.get("title", ""),
                                "text": str(item.get("text", "")).strip(),
                                "source": settings.ollama_chunk_model,
                            }
                        )
                    elif isinstance(item, str):
                        normalized.append({"title": "", "text": item.strip(), "source": settings.ollama_chunk_model})
                if normalized:
                    return normalized
        except Exception:
            pass
        return self._fallback_blocks(block)

    def _fast_blocks(self, block: str) -> list[dict[str, Any]]:
        if len(block) <= settings.chunk_max_size:
            return [{"title": "", "text": block, "source": "heuristic-fast"}]
        chunks: list[dict[str, Any]] = []
        start = 0
        step = settings.chunk_target_size
        while start < len(block):
            piece = block[start : start + settings.chunk_max_size]
            chunks.append({"title": "", "text": piece, "source": "heuristic-fast"})
            start += step
        return chunks

    def _chapter_blocks(self, text: str) -> list[str]:
        patterns = [
            r"(?=第[一二三四五六七八九十百千0-9]+回)",
            r"(?=第[一二三四五六七八九十百千0-9]+章)",
            r"(?=第[一二三四五六七八九十百千0-9]+节)",
        ]
        parts = [text]
        for pattern in patterns:
            new_parts: list[str] = []
            for part in parts:
                split = [segment.strip() for segment in re.split(pattern, part) if segment.strip()]
                if len(split) > 1:
                    new_parts.extend(split)
                else:
                    new_parts.append(part)
            parts = new_parts

        blocks: list[str] = []
        for part in parts:
            if len(part) <= 12000:
                blocks.append(part)
            else:
                blocks.extend(self._coarse_blocks(part))
        if not blocks:
            return self._coarse_blocks(text)
        return blocks

    def _coarse_blocks(self, text: str) -> list[str]:
        blocks: list[str] = []
        start = 0
        step = 10000
        size = 12000
        while start < len(text):
            blocks.append(text[start : start + size])
            start += step
        return blocks

    def _fallback_blocks(self, block: str) -> list[dict[str, Any]]:
        if len(block) <= settings.chunk_max_size:
            return [{"title": "", "text": block, "source": "heuristic"}]
        chunks: list[dict[str, Any]] = []
        start = 0
        while start < len(block):
            chunks.append({"title": "", "text": block[start : start + settings.chunk_max_size], "source": "heuristic"})
            start += settings.chunk_target_size
        return chunks

    def _emit_progress(self, progress_callback: ProgressCallback | None, **progress: Any) -> None:
        if progress_callback:
            progress_callback(progress)


ingestor = FourClassicsIngestor()
