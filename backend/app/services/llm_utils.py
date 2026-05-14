"""LLM utility helpers shared by manufacturing agents."""

from __future__ import annotations

import asyncio
import json
from typing import Any


def parse_json_response(content: str) -> dict[str, Any]:
    """Parse strict JSON, tolerating a surrounding markdown code fence."""
    content = content.strip()
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())


async def safe_llm_call(chain: Any, inputs: dict[str, Any]) -> str:
    """Call a LangChain-style chain with three exponential-backoff attempts."""
    delay_seconds = 2
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            response = await chain.ainvoke(inputs)
            return getattr(response, "content", response)
        except Exception as exc:  # pragma: no cover - exercised by integration clients
            last_error = exc
            if attempt == 2:
                break
            await asyncio.sleep(delay_seconds)
            delay_seconds = min(delay_seconds * 2, 10)

    assert last_error is not None
    raise last_error


def token_count(text: str) -> int:
    """Return a GPT-4o-ish token count with a dependency-free fallback."""
    try:
        import tiktoken

        return len(tiktoken.encoding_for_model("gpt-4o").encode(text))
    except Exception:
        return max(1, len(text) // 4)
