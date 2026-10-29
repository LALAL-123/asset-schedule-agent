"""工具注册、参数检查与故障注入。

业务工具都是本地函数；故障注入让测试和评估能稳定复现“工具失败”场景。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

# 每个工具都会自动多一个必填参数：模型用一句话写出“为什么选这个动作”。
# 执行工具前会剥离它，只写进 Trace，作为决策依据（不是模型内部思维过程）。
DECISION_NOTE = "decision_note"


class ToolError(Exception):
    """业务工具可预期的失败，例如存储不可用、对象不存在。"""


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema，type=object
    fn: Callable[..., Any]

    def schema(self) -> dict:
        params = copy.deepcopy(self.parameters)
        params.setdefault("type", "object")
        params.setdefault("properties", {})[DECISION_NOTE] = {
            "type": "string",
            "description": "一句话说明选择该动作的依据（引用哪条工具结果或输入条件）",
        }
        required = params.setdefault("required", [])
        if DECISION_NOTE not in required:
            required.append(DECISION_NOTE)
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": params},
        }


class FaultPlan:
    """按用例注入工具故障。

    spec 例：{"save_draft": {"mode": "always", "error": "存储不可用"}}
    mode: always=每次失败；once=只失败第一次；times=失败前 N 次（配合 "times": N）。
    """

    def __init__(self, spec: dict | None = None):
        self.spec = spec or {}
        self.counts: dict[str, int] = {}

    def check(self, name: str) -> str | None:
        rule = self.spec.get(name)
        if not rule:
            return None
        n = self.counts.get(name, 0)
        self.counts[name] = n + 1
        mode = rule.get("mode", "always")
        limit = float("inf") if mode == "always" else (1 if mode == "once" else int(rule.get("times", 1)))
        if n < limit:
            return rule.get("error", f"{name} 服务暂不可用（注入故障）")
        return None


class ToolRegistry:
    def __init__(self, tools: list[Tool], faults: FaultPlan | None = None):
        self.tools = {t.name: t for t in tools}
        self.faults = faults or FaultPlan()

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self.tools.values()]

    def call(self, name: str, args: dict) -> dict:
        tool = self.tools.get(name)
        if tool is None:
            return {"ok": False, "error_type": "unknown_tool", "error": f"未知工具 {name}；可用工具：{sorted(self.tools)}"}
        missing = [k for k in tool.parameters.get("required", []) if k not in args]
        if missing:
            return {"ok": False, "error_type": "invalid_arguments", "error": f"缺少参数 {missing}"}
        injected = self.faults.check(name)
        if injected:
            return {"ok": False, "error_type": "tool_failure", "error": injected}
        try:
            result = tool.fn(**args)
        except ToolError as exc:
            return {"ok": False, "error_type": "tool_failure", "error": str(exc)}
        except (TypeError, ValueError) as exc:
            return {"ok": False, "error_type": "invalid_arguments", "error": str(exc)}
        if not isinstance(result, dict):
            result = {"value": result}
        result.setdefault("ok", True)
        return result
