from __future__ import annotations

import time
from typing import Any

import httpx

from app.kongming_agent.backend.app.core.config import settings


class DashScopeClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.dashscope_base_url).rstrip("/")
        self.api_key = api_key or settings.dashscope_api_key

    def embed_texts(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured.")
        if not texts:
            return []
        if len(texts) > settings.dashscope_embedding_batch_size:
            raise ValueError(
                f"DashScope batch size exceeds {settings.dashscope_embedding_batch_size}."
            )

        payload: dict[str, Any] = {
            "model": model or settings.dashscope_embedding_model,
            "input": texts,
            "encoding_format": "float",
        }
        if dimensions is not None:
            payload["dimensions"] = dimensions

        response = httpx.post(
            f"{self.base_url}/embeddings",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=settings.dashscope_embedding_request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("data")
        if not isinstance(items, list) or not items:
            raise ValueError("DashScope embedding response missing data.")

        ordered: list[list[float] | None] = [None] * len(texts)
        for item in items:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            embedding = item.get("embedding")
            if isinstance(index, int) and 0 <= index < len(ordered) and isinstance(embedding, list):
                ordered[index] = [float(value) for value in embedding]

        if any(embedding is None for embedding in ordered):
            raise ValueError("DashScope embedding response is incomplete.")
        return [embedding for embedding in ordered if embedding is not None]

    def embed_text(self, text: str, *, model: str | None = None, dimensions: int | None = None) -> list[float]:
        return self.embed_texts([text], model=model, dimensions=dimensions)[0]

    def preflight(self) -> dict[str, Any]:
        started_at = time.perf_counter()
        embedding = self.embed_text(
            "诸葛亮出师表",
            model=settings.dashscope_embedding_model,
            dimensions=settings.dashscope_embedding_dimensions,
        )
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "reachable": True,
            "base_url": self.base_url,
            "model": settings.dashscope_embedding_model,
            "dimension": len(embedding),
            "latency_ms": latency_ms,
            "api_key_present": bool(self.api_key),
            "batch_size": settings.dashscope_embedding_batch_size,
        }


dashscope_client = DashScopeClient()
