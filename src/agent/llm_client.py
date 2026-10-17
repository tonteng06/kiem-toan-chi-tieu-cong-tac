"""LLM client (TV2, Day 6): call_llm with retry, timeout and HTTP error logging.

Talks to any OpenAI-compatible `/chat/completions` endpoint using only the standard library, so no
new dependency is needed. Configuration comes from the environment (never from code):

    GROQ_API_KEY   required (LLM_API_KEY / OPENAI_API_KEY are accepted as fallbacks)
    LLM_BASE_URL   default https://api.groq.com/openai/v1
    GROQ_MODEL     default llama-3.3-70b-versatile (LLM_MODEL also accepted)
    LLM_TIMEOUT    seconds per request, default 30
    LLM_MAX_RETRIES  default 3 (attempts = 1 + retries)

Retried: timeouts, connection errors, HTTP 408/429/5xx (exponential backoff 1s, 2s, 4s ...).
Not retried: other 4xx (bad request, bad key, ...) and a missing key; retrying cannot fix them.
Every failure raises LLMError; `run_agent` turns that into a clean `llm_error` stop. The API key is
never logged. There is NO silent fallback to a fake model: without a key or after a failure the call
raises, so a "real" run can never be mock output. Usage comes from the response and is returned
inside `ModelReply`, so `run_agent` sums it per question (calls, prompt_tokens, completion_tokens,
max_prompt).
"""
from __future__ import annotations

import json
import logging
import os
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from src.agent.agent import LLM, ModelReply

logger = logging.getLogger("agent.llm")

RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class LLMError(Exception):
    """The model call failed for good (after retries, or not retryable)."""


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str = "https://api.groq.com/openai/v1"
    model: str = "llama-3.3-70b-versatile"
    timeout: float = 30.0
    max_retries: int = 3
    temperature: float = 0.0
    json_mode: bool = True  # ask for a JSON object; the agent protocol is JSON (the prompt says so)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> LLMConfig:
        env = os.environ if env is None else env
        return cls(
            api_key=env.get("GROQ_API_KEY") or env.get("LLM_API_KEY") or env.get("OPENAI_API_KEY") or "",
            base_url=env.get("LLM_BASE_URL", cls.base_url).rstrip("/"),
            model=env.get("GROQ_MODEL") or env.get("LLM_MODEL") or cls.model,
            timeout=float(env.get("LLM_TIMEOUT", cls.timeout)),
            max_retries=int(env.get("LLM_MAX_RETRIES", cls.max_retries)),
        )


# (url, headers, body bytes, timeout) -> (status, response text). Raises OSError on network failure.
Transport = Callable[[str, dict, bytes, float], tuple[int, str]]


def urllib_transport(url: str, headers: dict, body: bytes, timeout: float) -> tuple[int, str]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:  # an HTTP status is a result, not a network failure
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:  # DNS failure, refused connection, ...
        raise OSError(str(exc.reason)) from None
    except socket.timeout:
        raise TimeoutError("request timed out") from None


def _parse_reply(text: str) -> ModelReply:
    try:
        data = json.loads(text)
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        prompt, completion = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError):
        raise LLMError("response is not a valid chat completion") from None
    if not isinstance(content, str) or type(prompt) is not int or type(completion) is not int:
        raise LLMError("response has an unexpected content or usage format")
    return ModelReply(content, prompt_tokens=prompt, completion_tokens=completion)


def call_llm(
    messages: list[dict],
    config: LLMConfig,
    transport: Transport = urllib_transport,
    sleep: Callable[[float], None] = time.sleep,
) -> ModelReply:
    if not config.api_key:
        raise LLMError("no API key: set GROQ_API_KEY in the environment")
    url = f"{config.base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
    payload = {"model": config.model, "messages": messages, "temperature": config.temperature}
    if config.json_mode:
        payload["response_format"] = {"type": "json_object"}
    body = json.dumps(payload).encode()

    attempts = config.max_retries + 1
    for attempt in range(1, attempts + 1):
        reason = ""
        try:
            status, text = transport(url, headers, body, config.timeout)
        except (OSError, TimeoutError) as exc:  # includes socket errors and timeouts
            reason = f"{type(exc).__name__}: {exc}"
            logger.error("LLM request failed (attempt %d/%d): %s", attempt, attempts, reason)
        else:
            if status == 200:
                return _parse_reply(text)
            reason = f"HTTP {status}"
            logger.error("LLM HTTP error %d (attempt %d/%d): %s", status, attempt, attempts, text[:300])
            if status not in RETRY_STATUS:
                raise LLMError(f"{reason} (not retryable): {text[:200]}")
        if attempt < attempts:
            sleep(2 ** (attempt - 1))
    raise LLMError(f"gave up after {attempts} attempts: {reason}")


def make_llm(config: LLMConfig | None = None, **kwargs) -> LLM:
    """Adapter with the `LLM` signature `run_agent` expects: (messages, tool schemas) -> ModelReply.

    The tool schemas are already part of the system prompt, so they are not sent separately.
    """
    config = config or LLMConfig.from_env()
    return lambda messages, schemas: call_llm(messages, config, **kwargs)