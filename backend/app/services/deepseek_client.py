from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import httpx

from app.kongming_agent.backend.app.core.config import settings


class DeepSeekClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or settings.deepseek_api_key or ""
        self.base_url = (base_url or settings.deepseek_base_url).rstrip("/")

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

        payload: dict[str, Any] = {
            "model": model or settings.deepseek_chat_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.default_max_tokens,
            "stream": False,
        }

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout or settings.deepseek_chat_timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("DeepSeek API response missing choices.")
        content = choices[0].get("message", {}).get("content", "")
        return content

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> Generator[str, None, None]:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

        payload: dict[str, Any] = {
            "model": model or settings.deepseek_chat_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else settings.default_max_tokens,
            "stream": True,
        }

        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout or settings.deepseek_chat_timeout,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[len("data: "):]
                if data_str == "[DONE]":
                    return
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    def preflight(self) -> dict[str, Any]:
        import time

        started_at = time.perf_counter()
        try:
            self.chat(
                messages=[{"role": "user", "content": "响应OK即可"}],
                max_tokens=10,
            )
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            return {
                "reachable": True,
                "base_url": self.base_url,
                "model": settings.deepseek_chat_model,
                "latency_ms": latency_ms,
                "api_key_present": bool(self.api_key),
            }
        except Exception as exc:
            return {
                "reachable": False,
                "base_url": self.base_url,
                "model": settings.deepseek_chat_model,
                "api_key_present": bool(self.api_key),
                "error": str(exc),
            }


deepseek_client = DeepSeekClient()
