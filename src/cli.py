"""命令行入口。

  python -m src.cli run examples/cases/c04_slot_conflict.json --llm mock
  python -m src.cli eval --llm mock          # 跑全部用例，写 examples/runs 与 examples/results
  python -m src.cli eval --llm openai        # 真实模型（需 .env 中的 LLM_API_KEY）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

from . import domain
from .core.llm import OpenAICompatLLM, ScriptedLLM
from .core.runner import check_case, load_case, run_case
from .core.trace import render_markdown, write_run

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "examples" / "cases"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def make_llm(kind: str):
    if kind == "mock":
        return ScriptedLLM(domain.mock_policy)
    load_dotenv()
    return OpenAICompatLLM.from_env()


def llm_tag(llm) -> str:
    return "mock" if llm.name.startswith("mock") else re.sub(r"[^A-Za-z0-9._-]+", "_", llm.name.split(":", 1)[1])


def cmd_run(args) -> int:
    case = load_case(args.case)
    llm = make_llm(args.llm)
    store = ROOT / "runtime" / "cli" / case["case_id"]
    if args.fresh and store.exists():
        shutil.rmtree(store)
    outputs = run_case(case, domain, llm, store)
    for i, (request, result) in enumerate(outputs, 1):
        print(render_markdown(result, f"{case['case_id']} 第 {i} 次运行", request))
    checks = check_case(case, domain, [r for _, r in outputs], store)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"] + (f"  ({c['detail']})" if c["detail"] else ""))
    return 0 if all(c["ok"] for c in checks) else 1


def cmd_eval(args) -> int:
    llm = make_llm(args.llm)
    tag = args.tag or llm_tag(llm)
    runs_dir = ROOT / "examples" / "runs" / tag
    if runs_dir.exists():
        shutil.rmtree(runs_dir)
    wanted = set(args.cases.split(",")) if args.cases else None
    rows, details = [], []
    for path in sorted(CASES.glob("*.json")):
        case = load_case(path)
        if wanted and case["case_id"] not in wanted:
            continue
        store = ROOT / "runtime" / "eval" / tag / case["case_id"]
        if store.exists():
            shutil.rmtree(store)
        outputs = run_case(case, domain, llm, store)
        for i, (request, result) in enumerate(outputs, 1):
            stem = case["case_id"] + (f"_run{i}" if len(outputs) > 1 else "")
            write_run(result, runs_dir, stem, f"{case['case_id']}：{case['title']}（运行 {i}/{len(outputs)}）", request)
        checks = check_case(case, domain, [r for _, r in outputs], store)
        passed = sum(c["ok"] for c in checks)
        statuses = " → ".join(r.status for _, r in outputs)
        rows.append(f"| {case['case_id']} | {'、'.join(case.get('covers', []))} | {statuses} | {passed}/{len(checks)} |")
        details.append({"case_id": case["case_id"], "statuses": statuses, "checks": checks})
        print(f"{case['case_id']}: {statuses}  checks {passed}/{len(checks)}")
    res_dir = ROOT / "examples" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    total = sum(len(d["checks"]) for d in details)
    ok = sum(c["ok"] for d in details for c in d["checks"])
    md = [f"# 验收结果（{llm.name}）", "", f"检查通过 {ok}/{total}。逐条 Trace 见 `examples/runs/{tag}/`。", "",
          "| 用例 | 覆盖验收点 | 结束状态 | 检查通过 |", "|---|---|---|---|", *rows, "", "## 未通过的检查", ""]
    fails = [f"- {d['case_id']}：{c['check']}（{c['detail']}）" for d in details for c in d["checks"] if not c["ok"]]
    md += fails or ["无"]
    (res_dir / f"{tag}-summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (res_dir / f"{tag}-summary.json").write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"检查通过 {ok}/{total}；汇总写入 examples/results/{tag}-summary.md")
    return 0 if ok == total else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m src.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="运行单个用例（也可用自己写的用例文件）")
    p_run.add_argument("case")
    p_run.add_argument("--llm", choices=["mock", "openai"], default="mock")
    p_run.add_argument("--fresh", action="store_true", help="清空该用例的本地存储后再跑")
    p_run.set_defaults(func=cmd_run)
    p_eval = sub.add_parser("eval", help="运行全部用例并写出 Trace 与汇总")
    p_eval.add_argument("--llm", choices=["mock", "openai"], default="mock")
    p_eval.add_argument("--cases", help="逗号分隔的 case_id，只跑这些")
    p_eval.add_argument("--tag", help="结果目录名（默认用模型名），用于区分不同轮次")
    p_eval.set_defaults(func=cmd_eval)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
