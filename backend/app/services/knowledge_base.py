from __future__ import annotations

import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.knowledge_ingestion import ProgressCallback, ingestor
from app.services.milvus_store import get_milvus_store


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _query_terms(query: str) -> list[str]:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", query)
    tokens = [token for token in cleaned.split() if token]
    terms: list[str] = []
    for token in tokens:
        terms.append(token)
        if len(token) > 1:
            for size in range(2, min(5, len(token) + 1)):
                for i in range(len(token) - size + 1):
                    terms.append(token[i : i + size])
    return list(dict.fromkeys(terms))


@dataclass
class KnowledgeChunk:
    chunk_id: str
    corpus_name: str
    doc_title: str
    text: str
    metadata: dict[str, Any]


class FourClassicsKnowledgeBase:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or settings.project_root
        self._chunks: list[KnowledgeChunk] | None = None
        self.milvus = get_milvus_store()

    def load(self) -> list[KnowledgeChunk]:
        if self._chunks is not None:
            return self._chunks

        chunks: list[KnowledgeChunk] = []
        txt_files = sorted(self.project_root.glob("*.txt"))
        for file_path in txt_files:
            corpus_name = file_path.stem
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            chunks.extend(self._split_document(corpus_name, file_path.name, text))
        self._chunks = chunks
        return chunks

    def _split_document(self, corpus_name: str, doc_title: str, text: str) -> list[KnowledgeChunk]:
        cleaned = _normalize_text(text)
        if not cleaned:
            return []

        segments = re.split(r"\n{2,}|(?=第[一二三四五六七八九十百千0-9]+回)", text)
        segments = [segment.strip() for segment in segments if segment.strip()]
        if not segments:
            segments = [cleaned]

        results: list[KnowledgeChunk] = []
        idx = 1
        for segment in segments:
            segment = segment.strip()
            if len(segment) <= 900:
                results.append(
                    KnowledgeChunk(
                        chunk_id=f"{corpus_name}_{idx:05d}",
                        corpus_name=corpus_name,
                        doc_title=doc_title,
                        text=segment,
                        metadata={"chunk_index": idx},
                    )
                )
                idx += 1
                continue

            start = 0
            while start < len(segment):
                piece = segment[start : start + 900]
                results.append(
                    KnowledgeChunk(
                        chunk_id=f"{corpus_name}_{idx:05d}",
                        corpus_name=corpus_name,
                        doc_title=doc_title,
                        text=piece,
                        metadata={"chunk_index": idx},
                    )
                )
                idx += 1
                start += 700
        return results

    def search(self, query: str, top_k: int = 4, corpus_name: str | None = None) -> list[dict[str, Any]]:
        if self._can_use_milvus():
            vector = ingestor.embed_query(query)
            try:
                results = self.milvus.search(vector, top_k=top_k, corpus_name=corpus_name)
                if results:
                    return [
                        {
                            "chunk_id": item["chunk_id"],
                            "doc_title": item["doc_title"],
                            "corpus_name": item["corpus_name"],
                            "score": round(item["score"], 4),
                            "excerpt": self._excerpt(item["chunk_text"], query),
                            "metadata": item["metadata"],
                        }
                        for item in results
                    ]
            except Exception:
                pass

        chunks = self.load()
        terms = _query_terms(query)
        scored: list[tuple[float, KnowledgeChunk]] = []

        for chunk in chunks:
            if corpus_name and corpus_name not in chunk.corpus_name:
                continue
            score = self._score(query, terms, chunk.text)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, chunk in scored[:top_k]:
            excerpt = self._excerpt(chunk.text, query)
            results.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_title": chunk.doc_title,
                    "corpus_name": chunk.corpus_name,
                    "score": round(score, 4),
                    "excerpt": excerpt,
                    "metadata": chunk.metadata,
                }
            )
        return results

    def _score(self, query: str, terms: list[str], text: str) -> float:
        lowered = text.lower()
        match_score = sum(2.0 for term in terms if term and term.lower() in lowered)
        fuzzy_score = SequenceMatcher(None, query, text[:1200]).ratio() * 2.0
        density = min(1.0, len(set(terms)) / max(1, len(terms)))
        length_factor = min(1.0, math.log(len(text) + 1) / 8)
        return match_score + fuzzy_score + density + length_factor

    def _excerpt(self, text: str, query: str, limit: int = 220) -> str:
        idx = text.find(query)
        if idx == -1:
            return text[:limit].strip()
        start = max(0, idx - 60)
        end = min(len(text), idx + limit)
        return text[start:end].strip()

    def rebuild_vector_store(self, progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
        return ingestor.ingest_all(force=True, progress_callback=progress_callback)

    def _can_use_milvus(self) -> bool:
        try:
            return self.milvus.has_data()
        except Exception:
            return False
