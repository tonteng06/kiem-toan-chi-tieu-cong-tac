"""Manual agent loop (TV2, Day 4).

model decides -> parse action -> validate args -> execute tool -> append observation -> repeat
-> final answer. The loop is bounded by MAX_STEPS, never evaluates model output, and never lets
a bad model reply or a tool error kill the run.

The model is a plain callable (`LLM`), so the loop runs with a scripted model in tests and with a
real provider later. Tools come from a "toolbox" with `schemas()` and `call(name, args) -> str`:
`RegistryToolbox` wraps the local registry; TV3's `McpToolbox` has the same two methods.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from src.agent.dispatcher import ERROR_PREFIX, dispatch, is_error
from src.agent.tool_registry import ToolRegistry

MAX_STEPS = 8
VALID_DECISIONS = {"APPROVED", "REJECTED", "ESCALATED", "NEED_MORE_INFO", "NO_ANSWER"}
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "agent_system.txt"


class Toolbox(Protocol):
    def schemas(self) -> list[dict]: ...
    def call(self, name: Any, args: Any = None) -> str: ...


class RegistryToolbox:
    """Local tools behind the same two-method port as the MCP toolbox."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def schemas(self) -> list[dict]:
        return self.registry.schemas()

    def call(self, name: Any, args: Any = None) -> str:
        return dispatch(self.registry, name, args)


@dataclass
class ModelReply:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


LLM = Callable[[list[dict], list[dict]], ModelReply]  # (messages, tool schemas) -> reply


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    max_prompt: int = 0

    def add(self, reply: ModelReply) -> None:
        self.calls += 1
        self.prompt_tokens += reply.prompt_tokens
        self.completion_tokens += reply.completion_tokens
        self.max_prompt = max(self.max_prompt, reply.prompt_tokens)


@dataclass
class Action:
    kind: str  # "tool" or "final"
    name: str = ""
    args: dict = field(default_factory=dict)
    decision: str = ""
    answer: str = ""
    evidence_refs: list[str] = field(default_factory=list)


class ActionParseError(ValueError):
    pass


def _first_json_object(text: str) -> Any:
    """Decode the first JSON object in `text` (models sometimes wrap it in prose or a code fence)."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            obj, _ = decoder.raw_decode(text[start:])
            return obj
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
    raise ActionParseError("reply must be one JSON object")


def parse_action(text: Any) -> Action:
    """Turn the model's reply into an Action. Raises ActionParseError, never anything else."""
    if not isinstance(text, str) or not text.strip():
        raise ActionParseError("reply is empty")
    obj = _first_json_object(text)
    if not isinstance(obj, dict):
        raise ActionParseError("reply must be a JSON object")
    kind = obj.get("action")
    if kind == "tool":
        name = obj.get("name")
        args = obj.get("args", {})
        if not isinstance(name, str) or not name:
            raise ActionParseError('tool action needs a string "name"')
        if isinstance(args, str):  # some models send arguments as a JSON string
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                raise ActionParseError('"args" is not valid JSON') from None
        if not isinstance(args, dict):
            raise ActionParseError('"args" must be a JSON object')
        return Action("tool", name=name, args=args)
    if kind == "final":
        decision, answer, refs = obj.get("decision"), obj.get("answer"), obj.get("evidence_refs", [])
        if decision not in VALID_DECISIONS:
            raise ActionParseError(f'"decision" must be one of {sorted(VALID_DECISIONS)}')
        if not isinstance(answer, str) or not answer.strip():
            raise ActionParseError('final action needs a non-empty "answer"')
        if not isinstance(refs, list) or not all(isinstance(r, str) and r.strip() for r in refs):
            raise ActionParseError('"evidence_refs" must be a list of non-empty strings')
        return Action("final", decision=decision, answer=answer, evidence_refs=refs)
    raise ActionParseError('"action" must be "tool" or "final"')


def load_system_prompt(schemas: list[dict] | None = None) -> str:
    prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    if schemas:
        prompt += "\nTools:\n" + json.dumps(schemas, ensure_ascii=False, indent=1)
    return prompt


def run_agent(
    question: str,
    llm: LLM,
    toolbox: Toolbox,
    max_steps: int = MAX_STEPS,
    system_prompt: str | None = None,
) -> dict:
    """Run the loop. Returns a dict that satisfies Member 1's AgentEvalOutput, plus the trace.

    `stopped_reason` is "final", "max_steps" or "llm_error". Only a valid final reply produces
    a real decision; every other ending is NO_ANSWER, so the agent never approves by accident.
    """
    schemas = toolbox.schemas()
    messages: list[dict] = [
        {"role": "system", "content": system_prompt or load_system_prompt(schemas)},
        {"role": "user", "content": question},
    ]
    usage, trace = Usage(), []

    def result(decision: str, answer: str, refs: list[str], reason: str) -> dict:
        return {
            "answer": answer, "decision": decision, "evidence_refs": refs, "usage": vars(usage).copy(),
            "stopped_reason": reason, "steps": len(trace), "trace": trace,
        }

    for step in range(1, max_steps + 1):
        try:
            reply = llm(messages, schemas)
        except Exception as exc:  # a provider failure must not crash the run
            return result("NO_ANSWER", f"The model call failed ({type(exc).__name__}: {exc}).", [], "llm_error")
        usage.add(reply)
        messages.append({"role": "assistant", "content": reply.text})
        entry: dict = {"step": step, "model_reply": reply.text}
        trace.append(entry)

        try:
            action = parse_action(reply.text)
        except ActionParseError as exc:
            entry["observation"] = f"{ERROR_PREFIX}bad reply format: {exc}"
            messages.append({"role": "user", "content": entry["observation"]})
            continue

        if action.kind == "final":
            entry["final"] = {"decision": action.decision, "evidence_refs": action.evidence_refs}
            return result(action.decision, action.answer, action.evidence_refs, "final")

        entry["tool"], entry["args"] = action.name, action.args
        observation = toolbox.call(action.name, action.args)
        entry["observation"], entry["is_error"] = observation, is_error(observation)
        messages.append({"role": "user", "content": f"Tool result for {action.name}: {observation}"})

    return result(
        "NO_ANSWER",
        f"Stopped after {max_steps} steps without a final answer; no decision was made.",
        [], "max_steps",
    )