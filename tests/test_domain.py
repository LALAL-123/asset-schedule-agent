"""题 1 业务工具与护栏测试。"""
import json
from pathlib import Path

import pytest

from src import domain
from src.core.agent import ToolRecord
from src.core.llm import ScriptedLLM
from src.core.runner import check_case, load_case, run_case
from src.domain.tools import build_tools, load_json, review

CASES = sorted((Path(__file__).resolve().parent.parent / "examples" / "cases").glob("*.json"))
REQ = {"request_id": "T1", "items": [
    {"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "18:00", "time_rule": "flexible"},
    {"asset_id": "M04", "channel": "douyin", "date": "2026-11-04", "time": "19:00", "time_rule": "flexible"}]}


def tools(tmp_path, request=REQ, env=None):
    return {t.name: t.fn for t in build_tools(request=request, env=env or {}, store_dir=tmp_path)}


def test_query_slots_reports_conflict_and_nearest_free(tmp_path):
    r = tools(tmp_path)["query_slots"]("douyin", "2026-11-03", "18:00")
    assert r["available"] is False and r["occupied_by"] == "X91"
    assert r["free_slots_nearby"][0] == "19:00"


def test_license_lookup_changes_review_verdict():
    assets = {a["asset_id"]: a for a in load_json("assets.json")}
    rules, lic = load_json("rules.json")["rules"], load_json("licenses.json")
    assert review(assets["M05"], rules)[0] == "needs_verification"
    assert review(assets["M05"], rules, lic)[0] == "pass"
    assert review(assets["M06"], rules, lic)[0] == "risk"


def test_save_draft_is_idempotent_per_request(tmp_path):
    t = tools(tmp_path)
    item = [{"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "19:00"}]
    a, b = t["save_draft"](item), t["save_draft"](item)
    assert a["draft_id"] == b["draft_id"] and b["deduplicated"] is True
    drafts = json.loads((tmp_path / "drafts.json").read_text(encoding="utf-8"))
    assert len(drafts) == 1 and drafts["T1"]["items"][0]["confirmed"] is False
    c = t["save_draft"]([{**item[0], "time": "21:00"}])
    assert c["draft_id"] == a["draft_id"] and c["version"] == 2


def test_save_draft_rejects_risk_occupied_and_fixed_change(tmp_path):
    t = tools(tmp_path)
    r = t["save_draft"]([{"asset_id": "M04", "channel": "douyin", "date": "2026-11-04", "time": "19:00"},
                         {"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "18:00"}])
    assert r["ok"] is False and len(r["errors"]) == 2
    fixed = {"request_id": "T2", "items": [{**REQ["items"][0], "time_rule": "fixed"}]}
    r2 = tools(tmp_path, fixed)["save_draft"]([{"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "19:00"}])
    assert r2["ok"] is False and "硬性" in r2["errors"][0]


def rec(tool, args, result, step=1):
    return ToolRecord(step, tool, args, {"ok": True, **result})


PASS_M01 = [rec("read_asset", {"asset_id": "M01"}, {"found": True}),
            rec("check_rules", {"asset_id": "M01"}, {"found": True, "result": "pass", "issues": []})]
ONE = {"request_id": "G", "items": [REQ["items"][0]]}


def finish(slot, saved=True, status="completed", summary="完成", conf=False):
    return {"items": [{"asset_id": "M01", "review_status": "approved", "suggested_slot": slot,
                       "slot_status": "as_requested", "needs_confirmation": conf}],
            "draft": {"saved": saved}, "task_status": status, "summary": summary}


def test_guard_rejects_false_save_claim_and_unqueried_slot():
    final, fixes = domain.guard(finish("2026-11-03 19:00"), PASS_M01, ONE)
    assert final["items"][0]["suggested_slot"] is None
    assert final["draft"]["saved"] is False
    assert any("未经 query_slots" in f for f in fixes) and any("saved=False" in f for f in fixes)


def test_guard_forces_confirmation_and_scrubs_publish_claim():
    q = rec("query_slots", {"channel": "douyin", "date": "2026-11-03", "time": "18:00"},
            {"channel": "douyin", "date": "2026-11-03", "requested_time": "18:00", "available": False, "free_slots_nearby": ["19:00"]})
    s = rec("save_draft", {}, {"draft_id": "D1", "version": 1, "deduplicated": False,
                               "items": [{"asset_id": "M01", "slot": "2026-11-03 19:00"}]})
    final, fixes = domain.guard(finish("2026-11-03 19:00", summary="M01 已发布"), PASS_M01 + [q, s], ONE)
    it = final["items"][0]
    assert it["needs_confirmation"] is True and final["task_status"] == "needs_confirmation"
    assert "已发布" not in final["summary"] and final["publish_status"] == "not_published"


def test_guard_downgrades_approved_when_rules_say_risk():
    recs = [rec("check_rules", {"asset_id": "M04"}, {"found": True, "result": "risk", "issues": [{"detail": "极限词"}]})]
    req = {"items": [REQ["items"][1]]}
    args = {"items": [{"asset_id": "M04", "review_status": "approved", "suggested_slot": "2026-11-04 19:00",
                       "slot_status": "as_requested", "needs_confirmation": False}],
            "draft": {"saved": False}, "task_status": "completed", "summary": ""}
    final, _ = domain.guard(args, recs, req)
    assert final["items"][0]["review_status"] == "risk_blocked" and final["items"][0]["suggested_slot"] is None
    assert final["task_status"] == "blocked"


@pytest.mark.parametrize("path", CASES, ids=lambda p: p.stem)
def test_case_acceptance_with_offline_mock(path, tmp_path):
    case = load_case(path)
    outputs = run_case(case, domain, ScriptedLLM(domain.mock_policy), tmp_path)
    checks = check_case(case, domain, [r for _, r in outputs], tmp_path)
    assert checks and all(c["ok"] for c in checks), [c for c in checks if not c["ok"]]


def test_guard_sends_incomplete_or_malformed_finish_back():
    req = {"items": REQ["items"]}
    with pytest.raises(ValueError, match="还没有做规则检查"):
        domain.guard(finish(""), PASS_M01, req)  # M04 未检查
    with pytest.raises(ValueError, match="单个时段"):
        domain.guard(finish("19:00, 16:00"), PASS_M01, ONE)


def test_lookup_license_does_not_mislead_on_owned_or_verified_music(tmp_path):
    t = tools(tmp_path)
    assert t["lookup_license"]("M01")["status"] == "not_required"  # 自有配乐
    assert t["lookup_license"]("M02")["status"] == "valid"         # 已核验配乐


QUERY_1800 = rec("query_slots", {"channel": "douyin", "date": "2026-11-03", "time": "18:00"},
                 {"channel": "douyin", "date": "2026-11-03", "requested_time": "18:00", "available": False,
                  "occupied_by": "X91", "free_slots_nearby": ["19:00", "16:00"]})


def test_guard_derives_slot_status_from_query_not_from_model():
    # 第 3 轮 GLM-4-Flash：查到有空闲时段却没选，模型/旧护栏都写成 no_free_slot
    no_pick = finish("", saved=False, status="needs_confirmation")
    no_pick["items"][0]["slot_status"] = "no_free_slot"
    final, _ = domain.guard(no_pick, PASS_M01 + [QUERY_1800], ONE)
    assert final["items"][0]["slot_status"] == "not_scheduled"
    fixed = {"request_id": "G", "items": [{**REQ["items"][0], "time_rule": "fixed"}]}
    final, _ = domain.guard(no_pick, PASS_M01 + [QUERY_1800], fixed)
    assert final["items"][0]["slot_status"] == "conflict_fixed"


def test_guard_keeps_slot_from_failed_save_attempt():
    req = {"request_id": "G", "items": [{**REQ["items"][0], "time": "19:00"}]}
    q = rec("query_slots", {"channel": "douyin", "date": "2026-11-03", "time": "19:00"},
            {"channel": "douyin", "date": "2026-11-03", "requested_time": "19:00", "available": True, "free_slots_nearby": []})
    save = ToolRecord(1, "save_draft", {"items": [{"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "19:00"}]},
                      {"ok": False, "error_type": "tool_failure", "error": "存储不可用"})
    final, _ = domain.guard(finish("", saved=False, status="save_failed"), PASS_M01 + [q, save], req)
    assert final["items"][0]["suggested_slot"] == "2026-11-03 19:00"
    assert final["task_status"] == "save_failed" and final["draft"]["saved"] is False
