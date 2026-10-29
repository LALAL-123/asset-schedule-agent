"""把一次运行写成 JSON（机器可读）和 Markdown（评审可读）。"""
from __future__ import annotations

import json
from pathlib import Path

from .agent import RunResult


def _cell(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(result: RunResult, title: str, request: dict) -> str:
    lines = [
        f"# {title}",
        "",
        f"- 模型：`{result.llm}`",
        f"- 结束状态：`{result.status}`（{result.stop_reason}）",
        f"- 决策轮数：{result.steps}；业务工具调用：{result.tool_calls}",
        "",
        "## 输入",
        "",
        "```json",
        json.dumps(request, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 执行记录",
        "",
        "| 步骤 | 动作 | 参数 | 返回摘要 | 决策依据 |",
        "|---|---|---|---|---|",
    ]
    for t in result.trace:
        if t["type"] == "tool_call":
            mark = ("" if t["ok"] else " ✗") + ("（从文本恢复）" if t.get("recovered_from_text") else "")
            lines.append(f"| {t['step']} | `{t['tool']}`{mark} | {_cell(t['arguments'])} | {_cell(t['observation'])} | {_cell(t['decision_note'])} |")
        elif t["type"] == "finish":
            lines.append(f"| {t['step']} | `finish` | status={t['status']} | 护栏校正 {len(t['guard_corrections'])} 处 | {_cell(t['decision_note'])} |")
        elif t["type"] == "stop":
            lines.append(f"| {t['step']} | **停止** | — | {t['status']}：{t['reason']} | 达到执行上限或模型服务异常 |")
        else:
            lines.append(f"| {t['step']} | {t['type']} | — | {_cell(t.get('content') or t.get('error', ''))} | — |")
    if result.guard_corrections:
        lines += ["", "## 护栏校正", ""] + [f"- {c}" for c in result.guard_corrections]
    lines += ["", "## 最终输出", "", "```json", json.dumps(result.final, ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def write_run(result: RunResult, out_dir: Path, stem: str, title: str, request: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {"title": title, "request": request, **result.to_dict()}
    (out_dir / f"{stem}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{stem}.md").write_text(render_markdown(result, title, request), encoding="utf-8")
