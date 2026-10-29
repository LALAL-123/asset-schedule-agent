"""验收检查：只看最终结果、工具调用事实和草稿存储，不绑定某一条执行路径。

因此同一套检查既用于离线 Mock，也用于真实模型评估。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .tools import load_json

PUBLISH = re.compile(r"已发布|发布成功|已上线")


def _item(res, aid):
    return next((i for i in res.final.get("items", []) if i["asset_id"] == aid), {})


def _drafts(store: Path) -> dict:
    p = store / "drafts.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _called(res, tool, **match) -> bool:
    return any(r.tool == tool and all(r.arguments.get(k) == v for k, v in match.items()) for r in res.records)


def _free(channel, date, time, extra=()):
    booked = load_json("schedule.json")["booked"] + list(extra)
    return not any((b["channel"], b["date"], b["time"]) == (channel, date, time) for b in booked)


def _no_publish(res):
    return ("未称已发布", not PUBLISH.search(res.final.get("summary", "")) and res.final.get("publish_status") == "not_published", "")


def c01(results, store):
    r = results[0]
    it = _item(r, "M02")
    d = _drafts(store)
    return [
        ("状态 completed", r.status == "completed", r.status),
        ("M02 审核通过且按要求排期", it.get("review_status") == "approved" and it.get("suggested_slot") == "2026-11-03 10:00", str(it)),
        ("无待确认项", not it.get("needs_confirmation"), ""),
        ("草稿已保存且仅 1 份", r.final["draft"]["saved"] and len(d) == 1, f"drafts={len(d)}"),
        _no_publish(r),
    ]


def c02(results, store):
    r = results[0]
    m03, m99 = _item(r, "M03"), _item(r, "M99")
    d = _drafts(store)
    return [
        ("M03 标为信息缺失", m03.get("review_status") == "missing_info", m03.get("review_status")),
        ("M03 原因写明缺失字段", any("cover" in x or "copyright" in x or "封面" in x or "版权" in x for x in m03.get("risk_reasons", [])), str(m03.get("risk_reasons"))),
        ("M99 标为不存在", m99.get("review_status") == "not_found", m99.get("review_status")),
        ("两项都未排期且待确认", not m03.get("suggested_slot") and not m99.get("suggested_slot") and m03.get("needs_confirmation") and m99.get("needs_confirmation"), ""),
        ("未保存任何草稿", not d, f"drafts={len(d)}"),
        ("状态 blocked", r.status == "blocked", r.status),
    ]


def c03(results, store):
    r = results[0]
    m4, m5, m6 = (_item(r, a) for a in ("M04", "M05", "M06"))
    saved = {i["asset_id"] for dr in _drafts(store).values() for i in dr["items"]}
    return [
        ("M04 极限词被阻断", m4.get("review_status") == "risk_blocked" and not m4.get("suggested_slot"), m4.get("review_status")),
        ("M05 先补查授权", _called(r, "lookup_license", asset_id="M05"), ""),
        ("M05 补查有效后排期", m5.get("review_status") == "approved" and m5.get("suggested_slot") == "2026-11-04 20:00", str(m5.get("suggested_slot"))),
        ("M06 补查过期后阻断", _called(r, "lookup_license", asset_id="M06") and m6.get("review_status") == "risk_blocked", m6.get("review_status")),
        ("草稿只含 M05", saved == {"M05"}, str(saved)),
        ("状态 needs_confirmation（有待处理素材）", r.status == "needs_confirmation", r.status),
    ]


def _alt_checks(r, store, extra_booked=(), forbid=("2026-11-03 18:00",)):
    it = _item(r, "M01")
    slot = it.get("suggested_slot") or ""
    date, _, time = slot.partition(" ")
    d = _drafts(store)
    saved = [i for dr in d.values() for i in dr["items"] if i["asset_id"] == "M01"]
    return [
        ("查询过要求时段", _called(r, "query_slots", channel="douyin", date="2026-11-03", time="18:00"), ""),
        ("建议时段为替代空闲时段", bool(slot) and slot not in forbid and _free("douyin", date, time, extra_booked), slot),
        ("标记待确认并有确认问题", it.get("needs_confirmation") is True and bool(it.get("confirmation_question")), ""),
        ("草稿中该项 confirmed=false", bool(saved) and saved[0]["confirmed"] is False, str(saved)),
        ("状态 needs_confirmation", r.status == "needs_confirmation", r.status),
        _no_publish(r),
    ]


def c04(results, store):
    r = results[0]
    checks = _alt_checks(r, store)
    checks.insert(2, ("建议为最近空闲的 19:00（参考实例）", _item(r, "M01").get("suggested_slot") == "2026-11-03 19:00",
                      _item(r, "M01").get("suggested_slot")))
    return checks


def c05(results, store):
    r = results[0]
    it = _item(r, "M01")
    saved = [i for dr in _drafts(store).values() for i in dr["items"] if i["asset_id"] == "M01"]
    return [
        ("硬性时间未被改动", not it.get("suggested_slot") and it.get("slot_status") == "conflict_fixed", f"{it.get('suggested_slot')} {it.get('slot_status')}"),
        ("请求用户确认", it.get("needs_confirmation") is True and bool(it.get("confirmation_question")), it.get("confirmation_question", "")),
        ("草稿中没有改时间的 M01", not saved, str(saved)),
        ("状态 blocked", r.status == "blocked", r.status),
    ]


def c06(results, store):
    a, b = results
    d = _drafts(store)
    return [
        ("两次都保存成功", a.final["draft"]["saved"] and b.final["draft"]["saved"], ""),
        ("两次是同一草稿 ID", a.final["draft"]["draft_id"] == b.final["draft"]["draft_id"], ""),
        ("存储中只有 1 份草稿、版本 1", len(d) == 1 and next(iter(d.values()))["version"] == 1, f"drafts={len(d)}"),
        ("第二次标记 deduplicated", b.final["draft"]["deduplicated"] is True, ""),
    ]


def c07(results, store):
    r = results[0]
    return [
        ("状态 save_failed", r.status == "save_failed", r.status),
        ("draft.saved=false 且带错误原因", r.final["draft"]["saved"] is False and bool(r.final["draft"]["error"]), str(r.final["draft"])),
        ("存储中没有草稿", not _drafts(store), ""),
        ("summary 未声称保存成功", "保存成功" not in r.final["summary"] and "失败" in r.final["summary"], r.final["summary"]),
        _no_publish(r),
    ]


def c08(results, store):
    first, second = results
    it = _item(second, "M01")
    d = _drafts(store)
    dr = next(iter(d.values()), {})
    return [
        ("首次运行待确认", first.status == "needs_confirmation", first.status),
        ("确认后排到用户同意的 19:00", it.get("suggested_slot") == "2026-11-03 19:00" and not it.get("needs_confirmation"), str(it)),
        ("确认后状态 completed", second.status == "completed", second.status),
        ("仍只有 1 份草稿，版本更新为 2 且已确认", len(d) == 1 and dr.get("version") == 2 and dr["items"][0]["confirmed"] is True, str(dr.get("items"))),
    ]


def c09(results, store):
    extra = [{"channel": "douyin", "date": "2026-11-03", "time": "19:00"}]
    return _alt_checks(results[0], store, extra, forbid=("2026-11-03 18:00", "2026-11-03 19:00"))


def c10(results, store):
    r = results[0]
    return [
        ("返回明确未完成状态", r.status == "incomplete" and r.final.get("stop_reason") == "step_limit_reached", r.status),
        ("决策轮数不超过上限", r.steps <= 3, str(r.steps)),
        ("未保存草稿", not _drafts(store), ""),
    ]


CHECKS = {
    "c01_normal": c01, "c02_missing_info": c02, "c03_rule_risk": c03, "c04_slot_conflict": c04,
    "c05_fixed_time_conflict": c05, "c06_duplicate_submit": c06, "c07_save_failure": c07,
    "c08_user_confirms_alternative": c08, "c09_conflict_shifted": c09, "c10_step_limit": c10,
}
