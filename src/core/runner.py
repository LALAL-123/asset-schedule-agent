"""按用例组装工具与 Agent、运行、并用验收检查评估结果。

用例文件（examples/cases/*.json）字段：
  case_id, title, covers(覆盖的验收点), request(任务输入),
  env(数据覆盖，可选), faults(故障注入，可选), max_steps(可选),
  runs(可选：多次提交同一请求，每次可带 request_patch / env / faults)
同一用例的多次运行共享同一个存储目录，用来验证“重复提交 / 续跑”。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType

from .agent import ReActAgent, RunResult
from .tools import FaultPlan, ToolRegistry


def load_case(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_case(case: dict, domain: ModuleType, llm, store_dir: Path) -> list[tuple[dict, RunResult]]:
    store_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for run in case.get("runs") or [{}]:
        request = {**case["request"], **run.get("request_patch", {})}
        env = {**case.get("env", {}), **run.get("env", {})}
        faults = FaultPlan(run.get("faults", case.get("faults")))
        registry = ToolRegistry(domain.build_tools(request=request, env=env, store_dir=store_dir), faults)
        agent = ReActAgent(
            llm=llm,
            registry=registry,
            system_prompt=domain.SYSTEM_PROMPT,
            finish_parameters=domain.FINISH_PARAMETERS,
            guard=domain.guard,
            on_incomplete=domain.on_incomplete,
            max_steps=case.get("max_steps", domain.MAX_STEPS),
            max_tool_calls=case.get("max_tool_calls", domain.MAX_TOOL_CALLS),
        )
        outputs.append((request, agent.run(request)))
    return outputs


def check_case(case: dict, domain: ModuleType, results: list[RunResult], store_dir: Path) -> list[dict]:
    fn = domain.CHECKS.get(case["case_id"])
    if fn is None:
        return []
    try:
        return [{"check": name, "ok": bool(ok), "detail": detail} for name, ok, detail in fn(results, store_dir)]
    except Exception as exc:  # 输出缺字段等情况：记为未通过，不中断整轮评估
        return [{"check": "检查执行出错（输出结构不完整）", "ok": False, "detail": f"{type(exc).__name__}: {exc}"}]
