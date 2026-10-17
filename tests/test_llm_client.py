import json

import pytest

from src.agent.agent import RegistryToolbox, run_agent
from src.agent.llm_client import LLMConfig, LLMError, call_llm, make_llm
from src.agent.tool_registry import build_registry

CFG = LLMConfig(api_key="test-key", max_retries=3)
MSGS = [{"role": "user", "content": "hi"}]


def ok_body(content='{"action": "final"}', prompt=120, completion=15):
    return json.dumps({"choices": [{"message": {"content": content}}],
                       "usage": {"prompt_tokens": prompt, "completion_tokens": completion}})


class FakeTransport:
    """Replays results in order: (status, text) tuples or exceptions to raise."""

    def __init__(self, *results):
        self.results, self.calls = list(results), []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, json.loads(body), timeout))
        r = self.results.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_success_returns_text_and_usage():
    t = FakeTransport((200, ok_body()))
    reply = call_llm(MSGS, CFG, transport=t, sleep=lambda s: None)
    assert (reply.text, reply.prompt_tokens, reply.completion_tokens) == ('{"action": "final"}', 120, 15)
    url, headers, payload, timeout = t.calls[0]
    assert url == "https://api.groq.com/openai/v1/chat/completions" and timeout == CFG.timeout
    assert headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "llama-3.3-70b-versatile" and payload["temperature"] == 0.0
    assert payload["response_format"] == {"type": "json_object"} and payload["messages"] == MSGS


def test_missing_key_fails_without_any_request():
    t = FakeTransport()
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        call_llm(MSGS, LLMConfig(api_key=""), transport=t, sleep=lambda s: None)
    assert t.calls == []  # and there is no fake-model fallback


@pytest.mark.parametrize("first", [(429, "slow down"), (503, "busy"), OSError("connection reset"),
                                   TimeoutError("timed out")])
def test_transient_failures_are_retried(first):
    t, sleeps = FakeTransport(first, (200, ok_body())), []
    reply = call_llm(MSGS, CFG, transport=t, sleep=sleeps.append)
    assert reply.completion_tokens == 15 and len(t.calls) == 2 and sleeps == [1]


def test_gives_up_after_retries_with_backoff():
    t, sleeps = FakeTransport(*[(500, "boom")] * 4), []
    with pytest.raises(LLMError, match="gave up after 4 attempts"):
        call_llm(MSGS, CFG, transport=t, sleep=sleeps.append)
    assert len(t.calls) == 4 and sleeps == [1, 2, 4]


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_client_errors_are_not_retried(status):
    t, sleeps = FakeTransport((status, "bad")), []
    with pytest.raises(LLMError, match="not retryable"):
        call_llm(MSGS, CFG, transport=t, sleep=sleeps.append)
    assert len(t.calls) == 1 and sleeps == []


@pytest.mark.parametrize("body", ["not json", "{}", '{"choices": []}',
                                  json.dumps({"choices": [{"message": {"content": None}}]}),
                                  ok_body(prompt="many")])
def test_malformed_provider_response_is_an_llm_error(body):
    with pytest.raises(LLMError):
        call_llm(MSGS, CFG, transport=FakeTransport((200, body)), sleep=lambda s: None)


def test_config_from_env_defaults_to_groq():
    cfg = LLMConfig.from_env({"GROQ_API_KEY": "k", "GROQ_MODEL": "m", "LLM_TIMEOUT": "5", "LLM_MAX_RETRIES": "1"})
    assert (cfg.api_key, cfg.model, cfg.timeout, cfg.max_retries) == ("k", "m", 5.0, 1)
    assert cfg.base_url == "https://api.groq.com/openai/v1"
    assert LLMConfig.from_env({}).api_key == ""


def test_agent_run_sums_real_usage_per_question(tmp_path):
    import shutil
    from pathlib import Path
    from src.agent.state_store import StateStore

    path = tmp_path / "claims.json"
    shutil.copy(Path(__file__).parents[1] / "data" / "claims" / "claims.json", path)
    toolbox = RegistryToolbox(build_registry(StateStore(path)))
    t = FakeTransport(
        (200, ok_body(json.dumps({"action": "tool", "name": "get_claim_status", "args": {"claim_id": "CLM-001"}}), 100, 10)),
        (200, ok_body(json.dumps({"action": "final", "decision": "NO_ANSWER", "answer": "x", "evidence_refs": []}), 300, 20)),
    )
    out = run_agent("q", make_llm(CFG, transport=t, sleep=lambda s: None), toolbox)
    assert out["usage"] == {"calls": 2, "prompt_tokens": 400, "completion_tokens": 30, "max_prompt": 300}


def test_provider_outage_ends_the_run_cleanly(tmp_path):
    t = FakeTransport(*[(503, "down")] * 4)
    out = run_agent("q", make_llm(CFG, transport=t, sleep=lambda s: None), RegistryToolbox(build_registry()))
    assert out["stopped_reason"] == "llm_error" and out["decision"] == "NO_ANSWER"