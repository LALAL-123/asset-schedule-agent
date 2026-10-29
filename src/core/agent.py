"""ReAct 循环：模型选择动作 → 执行工具 → 观察结果 → 模型决定下一步或结束。

循环本身不含业务分支：每一步做什么完全由模型（或离线 Mock 策略）根据已有观察决定。
代码只负责三件事：执行工具、限制步数和调用次数、在结束时用工具事实校验模型的结论（guard）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from .llm import USER_PREFIX, LLMReply, recover_text_tool_calls
from .tools import DECISION_NOTE, Tool, ToolRegistry

FINISH = "finish"
NUDGE = ("你上一条回复没有调用工具，纯文本系统无法执行。请用 function calling 调用工具推进任务；"
         "已经可以给出最终结果时调用 finish，把结果填进它的参数，不要直接用文字作答。")


@dataclass
class ToolRecord:
    step: int
    tool: str
    arguments: dict
    result: dict

    @property
    def ok(self) -> bool:
        return bool(self.result.get("ok"))


@dataclass
class RunResult:
    status: str
    stop_reason: str
    final: dict
    trace: list[dict]
    steps: int
    tool_calls: int
    llm: str
    guard_corrections: list[str] = field(default_factory=list)
    records: list[ToolRecord] = field(default_factory=list, repr=False)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "stop_reason": self.stop_reason,
            "llm": self.llm,
            "steps": self.steps,
            "tool_calls": self.tool_calls,
            "final": self.final,
            "guard_corrections": self.guard_corrections,
            "trace": self.trace,
        }


# guard(模型提交的 finish 参数, 已执行的工具记录, 任务输入) -> (校正后的最终结果, 校正说明)
Guard = Callable[[dict, list[ToolRecord], dict], tuple[dict, list[str]]]
# on_incomplete(工具记录, 任务输入, 停止原因) -> 未完成时的结果（保留已完成部分）
OnIncomplete = Callable[[list[ToolRecord], dict, str], dict]


def summarize(result: Any, limit: int = 360) -> str:
    text = json.dumps(result, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


class ReActAgent:
    def __init__(self, llm, registry: ToolRegistry, system_prompt: str, finish_parameters: dict,
                 guard: Guard, on_incomplete: OnIncomplete, max_steps: int = 10, max_tool_calls: int = 16):
        self.llm = llm
        self.registry = registry
        self.system_prompt = system_prompt
        self.guard = guard
        self.on_incomplete = on_incomplete
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.finish_tool = Tool(
            FINISH,
            "提交最终结构化结果。所有必要动作完成、或判断无法继续时调用；必须在看到上一轮工具结果后单独调用。",
            finish_parameters,
            fn=lambda **_: None,
        )

    def run(self, payload: dict) -> RunResult:
        tools = self.registry.schemas() + [self.finish_tool.schema()]
        system = (self.system_prompt + f"\n\n执行预算：最多 {self.max_steps} 轮决策、{self.max_tool_calls} 次业务工具调用，"
                  "超出后任务以未完成状态结束。")
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": USER_PREFIX + json.dumps(payload, ensure_ascii=False)},
        ]
        records: list[ToolRecord] = []
        trace: list[dict] = []
        calls = 0

        for step in range(1, self.max_steps + 1):
            try:
                reply = self.llm.chat(messages, tools)
            except Exception as exc:  # 模型服务异常：如实结束，不伪造结果
                trace.append({"step": step, "type": "llm_error", "error": str(exc)[:300]})
                return self._stop(records, payload, trace, step, calls, "failed", "llm_error")

            recovered = False
            if not reply.tool_calls:
                # 部分模型会把调用写成文本（“调用工具：finish 参数：{...}”）。只恢复写明了工具名和 JSON 参数的调用，
                # 动作和参数仍是模型给的；恢复的调用在 Trace 中标注。
                names = [t["function"]["name"] for t in tools]
                reply = LLMReply(reply.content, recover_text_tool_calls(reply.content, names, step))
                recovered = bool(reply.tool_calls)
            if not reply.tool_calls:
                trace.append({"step": step, "type": "no_tool_call", "content": reply.content[:300]})
                messages.append({"role": "assistant", "content": reply.content or ""})
                messages.append({"role": "user", "content": NUDGE})
                continue

            messages.append(_assistant_message(reply))
            has_business = any(c.name != FINISH for c in reply.tool_calls)
            done: tuple[dict, list[str], str] | None = None
            limit_hit = False

            for call in reply.tool_calls:
                note = str(call.arguments.pop(DECISION_NOTE, "") or "")
                if call.parse_error:
                    result = {"ok": False, "error_type": "invalid_arguments", "error": call.parse_error}
                elif call.name == FINISH:
                    if has_business:
                        result = {"ok": False, "error_type": "finish_rejected",
                                  "error": "finish 不能与其他工具同轮调用；请先查看这些工具的结果。"}
                    else:
                        try:
                            final, corrections = self.guard(dict(call.arguments), records, payload)
                            done = (final, corrections, note)
                            result = {"ok": True, "accepted": True}
                        except Exception as exc:  # finish 参数不合法：退回给模型修正
                            result = {"ok": False, "error_type": "invalid_finish", "error": str(exc)[:300]}
                elif calls >= self.max_tool_calls:
                    result = {"ok": False, "error_type": "tool_call_limit", "error": "已达到工具调用上限"}
                    limit_hit = True
                else:
                    calls += 1
                    result = self.registry.call(call.name, call.arguments)
                    records.append(ToolRecord(step, call.name, dict(call.arguments), result))

                if not (call.name == FINISH and done):
                    trace.append({"step": step, "type": "tool_call", "tool": call.name, "arguments": call.arguments,
                                  "decision_note": note, "ok": bool(result.get("ok")), "observation": summarize(result),
                                  "recovered_from_text": recovered})
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(result, ensure_ascii=False)})

            if done:
                final, corrections, note = done
                trace.append({"step": step, "type": "finish", "decision_note": note, "recovered_from_text": recovered,
                              "status": final.get("task_status"), "guard_corrections": corrections})
                return RunResult(final.get("task_status", "unknown"), "model_finished", final, trace,
                                 step, calls, self.llm.name, corrections, records)
            if limit_hit:
                return self._stop(records, payload, trace, step, calls, "incomplete", "tool_call_limit_reached")

        return self._stop(records, payload, trace, self.max_steps, calls, "incomplete", "step_limit_reached")

    def _stop(self, records, payload, trace, step, calls, status, reason) -> RunResult:
        final = self.on_incomplete(records, payload, reason)
        final["task_status"] = status
        final["stop_reason"] = reason
        trace.append({"step": step, "type": "stop", "status": status, "reason": reason})
        return RunResult(status, reason, final, trace, step, calls, self.llm.name, [], records)


def _assistant_message(reply: LLMReply) -> dict:
    return {
        "role": "assistant",
        "content": reply.content or "",
        "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.raw_arguments}}
            for c in reply.tool_calls
        ],
    }
