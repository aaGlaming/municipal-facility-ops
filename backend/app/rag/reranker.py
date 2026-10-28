"""OpenAI-compatible rerank provider with a deterministic fallback at the caller."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings


class RerankProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class RerankProvider:
    """Adapter for endpoints accepting query, documents, model and top_n."""

    def __init__(self, settings: Settings) -> None:
        if not settings.rerank_configured:
            raise RerankProviderError("rerank model is not configured", retryable=False)
        self.url = settings.rerank_url
        self.model = settings.rerank_model
        self._settings = settings

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        if not documents:
            return []
        payload = json.dumps(
            {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": min(top_n, len(documents)),
                "return_documents": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._settings.rerank_api_key not in {"", "replace_me"}:
            headers["Authorization"] = f"Bearer {self._settings.rerank_api_key}"
        attempts = self._settings.rerank_max_retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                request = Request(self.url, data=payload, headers=headers, method="POST")
                with urlopen(request, timeout=self._settings.rerank_timeout_seconds) as response:
                    body = json.loads(response.read().decode("utf-8"))
                return self._parse(body, len(documents))
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    time.sleep(min(2**attempt, 8))
        raise RerankProviderError("rerank provider request failed", retryable=True) from last_error

    @staticmethod
    def _parse(body: Any, document_count: int) -> list[tuple[int, float]]:
        raw_results = body.get("results") if isinstance(body, dict) else body
        if raw_results is None and isinstance(body, dict):
            raw_results = body.get("data")
        if not isinstance(raw_results, list):
            raise ValueError("rerank response does not contain results")
        results: list[tuple[int, float]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                raise ValueError("rerank result item is invalid")
            index = int(item["index"])
            score = float(item.get("relevance_score", item.get("score")))
            if not 0 <= index < document_count:
                raise ValueError("rerank result index is out of range")
            results.append((index, score))
        if not results:
            raise ValueError("rerank response is empty")
        return results


def get_rerank_provider(settings: Settings) -> RerankProvider:
    return RerankProvider(settings)
