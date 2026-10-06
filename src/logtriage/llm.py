from __future__ import annotations

import json
import os
from urllib import error, request


class LLMConfigurationError(RuntimeError):
    pass


def summarize_report(report: dict) -> str:
    """Summarize an aggregate report through an OpenAI-compatible HTTP endpoint.

    Only the aggregate report is transmitted; raw log lines are never sent.
    """
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()

    if not base_url or not api_key or not model:
        raise LLMConfigurationError(
            "Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL before using --ai-summary."
        )

    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise production support assistant. Analyze the "
                    "aggregate log diagnostics and identify likely priorities. Do "
                    "not invent root causes that are not supported by the data."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(report, ensure_ascii=False),
            },
        ],
        "temperature": 0.2,
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise RuntimeError("LLM response did not match the expected schema.") from exc
