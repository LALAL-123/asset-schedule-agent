"""模型接入。

- OpenAICompatLLM：真实模型，走 OpenAI 兼容的 Chat Completions + function calling。
- ScriptedLLM：离线 Mock，用确定性规则读取工具结果再选下一步。只验证循环、工具、
  护栏和 Trace 是否打通，不代表真实模型的决策效果。
"""
from __future__ import annotations

import itertools
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable

USER_PREFIX = "任务输入（JSON）：\n"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str = "{}"
    parse_error: str | None = None


@dataclass
class LLMReply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class OpenAICompatLLM:
    """兼容 OpenAI 接口的服务均可：OpenAI、DeepSeek、阿里百炼（通义）、Moonshot 等。"""

    def __init__(self, model: str, api_key: str, base_url: str | None = None,
                 temperature: float = 0.0, tool_choice: str = "auto", timeout: float = 60.0):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=timeout, max_retries=2)
        self.model = model
        self.temperature = temperature
        self.tool_choice = tool_choice
        self.name = f"openai-compat:{model}"

    @classmethod
    def from_env(cls) -> "OpenAICompatLLM":
        key = os.environ.get("LLM_API_KEY")
        if not key:
            raise RuntimeError("未设置 LLM_API_KEY：复制 .env.example 为 .env 并填写，或使用 --llm mock")
        return cls(
            model=os.environ.get("LLM_MODEL", "deepseek-chat"),
            api_key=key,
            base_url=os.environ.get("LLM_BASE_URL") or None,
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0")),
            tool_choice=os.environ.get("LLM_TOOL_CHOICE", "auto"),
        )

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMReply:
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools,
            tool_choice=self.tool_choice, temperature=self.temperature,
        )
        msg = resp.choices[0].message
        calls = []
        for tc in msg.tool_calls or []:
            raw = tc.function.arguments or "{}"
            err = None
            try:
                args = json.loads(raw)
                if not isinstance(args, dict):
                    args, err = {}, "参数不是 JSON 对象"
            except json.JSONDecodeError as exc:
                args, err = {}, f"参数 JSON 解析失败：{exc}"
            calls.append(ToolCall(tc.id, tc.function.name, args, raw, err))
        return LLMReply(msg.content or "", calls)


def recover_text_tool_calls(content: str, tool_names: list[str], step: int = 0) -> list[ToolCall]:
    """把写成文本的工具调用恢复为结构化调用（GLM-4-Flash 等模型偶尔这样输出）。

    条件严格：文本中出现已注册的工具名，且其后 40 个字符内紧跟一个可解析的 JSON 对象。
    只恢复第一个调用；不从自然语言里推断任何参数。
    """
    decoder = json.JSONDecoder()
    for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", content or ""):
        name = m.group(0)
        if name not in tool_names:
            continue
        brace = content.find("{", m.end())
        if brace == -1 or brace - m.end() > 40:
            continue
        try:
            obj, _ = decoder.raw_decode(content[brace:])
        except ValueError:
            continue
        if isinstance(obj, dict):
            return [ToolCall(f"text_{step}_1", name, obj, json.dumps(obj, ensure_ascii=False))]
    return []


@dataclass
class Observation:
    tool: str
    args: dict
    result: dict


def parse_conversation(messages: list[dict]) -> tuple[dict, list[Observation]]:
    """从对话中取出任务输入和按顺序排列的 (工具, 参数, 结果)。供 Mock 策略使用。"""
    payload: dict = {}
    for m in messages:
        if m["role"] == "user" and m["content"].startswith(USER_PREFIX):
            payload = json.loads(m["content"][len(USER_PREFIX):])
            break
    pending: dict[str, tuple[str, dict]] = {}
    obs: list[Observation] = []
    for m in messages:
        if m["role"] == "assistant":
            for tc in m.get("tool_calls") or []:
                args = json.loads(tc["function"]["arguments"] or "{}")
                args.pop("decision_note", None)
                pending[tc["id"]] = (tc["function"]["name"], args)
        elif m["role"] == "tool" and m["tool_call_id"] in pending:
            name, args = pending.pop(m["tool_call_id"])
            obs.append(Observation(name, args, json.loads(m["content"])))
    return payload, obs


# policy(payload, observations) -> (工具名, 决策依据, 参数)
Policy = Callable[[dict, list[Observation]], tuple[str, str, dict]]


class ScriptedLLM:
    def __init__(self, policy: Policy, name: str = "mock:scripted-policy"):
        self.policy = policy
        self.name = name
        self._ids = itertools.count(1)

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMReply:
        payload, obs = parse_conversation(messages)
        name, note, args = self.policy(payload, obs)
        args = {**args, "decision_note": note}
        return LLMReply("", [ToolCall(f"mock_{next(self._ids)}", name, args, json.dumps(args, ensure_ascii=False))])
