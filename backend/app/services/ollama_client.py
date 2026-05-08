from __future__ import annotations

import json
import math
import time
from hashlib import sha256
from typing import Any

import httpx

from app.kongming_agent.backend.app.core.config import settings


class OllamaClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    def chat(self, model: str, system: str, user: str, *, temperature: float = 0.2, format_json: bool = False) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": temperature},
        }
        if format_json:
            payload["format"] = "json"
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=settings.chat_request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    def embed(self, model: str, prompt: str) -> list[float]:
        return self.embed_batch(model, [prompt])[0]

    def embed_batch(self, model: str, prompts: list[str]) -> list[list[float]]:
        errors: list[str] = []
        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": model, "input": prompts},
                timeout=settings.embedding_request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings")
            if isinstance(embeddings, list) and embeddings:
                return [[float(value) for value in vec] for vec in embeddings]
            raise ValueError("ollama embed response missing embeddings")
        except Exception as exc:
            errors.append(f"/api/embed: {exc}")

        # fallback: try /api/embeddings one by one
        results: list[list[float]] = []
        for prompt in prompts:
            try:
                response = httpx.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model, "prompt": prompt},
                    timeout=settings.embedding_request_timeout,
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding")
                if not isinstance(embedding, list):
                    raise ValueError("ollama embeddings response missing embedding")
                results.append([float(value) for value in embedding])
            except Exception as exc:
                errors.append(f"/api/embeddings[{prompt[:30]}]: {exc}")
                raise RuntimeError("; ".join(errors)) from exc
        return results

    def json_chat(self, model: str, system: str, user: str, *, temperature: float = 0.1) -> Any:
        content = self.chat(model, system, user, temperature=temperature, format_json=True)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start : end + 1])
            raise

    def fallback_vector(self, text: str, dim: int) -> list[float]:
        digest = sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        counter = 0
        while len(values) < dim:
            block = sha256(digest + counter.to_bytes(4, "little")).digest()
            for offset in range(0, len(block), 4):
                if len(values) >= dim:
                    break
                raw = int.from_bytes(block[offset : offset + 4], "little", signed=False)
                values.append((raw / 2**32) * 2.0 - 1.0)
            counter += 1
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]

    def tags(self) -> dict[str, Any]:
        response = httpx.get(f"{self.base_url}/api/tags", timeout=10.0)
        response.raise_for_status()
        return response.json()

    def preflight(self, chunk_model: str) -> dict[str, Any]:
        started_at = time.perf_counter()
        tags_payload = self.tags()
        models = tags_payload.get("models") if isinstance(tags_payload, dict) else []
        names = []
        if isinstance(models, list):
            for item in models:
                if isinstance(item, dict) and item.get("name"):
                    names.append(str(item["name"]))
        return {
            "ollama_reachable": True,
            "available_models": names,
            "chunk_model": chunk_model,
            "chunk_model_present": chunk_model in names,
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
        }


ollama_client = OllamaClient()
