"""结束护栏：用工具返回的事实核对模型结论。

模型决定“做什么”；护栏只拦截与事实不符的结论：
审核未通过却排期、时段未经查询、擅改硬性时间、未确认却当作已确认、
虚报保存成功、称“已发布”。每次校正都写进 guard_corrections。
"""
from __future__ import annotations

import re

from ..core.agent import ToolRecord

PUBLISH_CLAIM = re.compile(r"已发布|发布成功|已上线|已经发布")
SLOT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def _last(records: list[ToolRecord], tool: str, **match) -> ToolRecord | None:
    for r in reversed(records):
        if r.tool == tool and all(r.arguments.get(k) == v for k, v in match.items()):
            return r
    return None


def review_truth(records: list[ToolRecord], aid: str) -> tuple[str, list[str]]:
    """根据已执行的工具结果推出该素材的审核结论。"""
    read = _last(records, "read_asset", asset_id=aid)
    if read and read.ok and read.result.get("found") is False:
        return "not_found", ["素材库中没有该 ID"]
    chk = _last(records, "check_rules", asset_id=aid)
    if chk is None or not chk.ok:
        return "unchecked", ["未完成规则检查"]
    if chk.result.get("found") is False:
        return "not_found", ["素材库中没有该 ID"]
    reasons = [i["detail"] for i in chk.result.get("issues", [])]
    result = chk.result.get("result")
    if result == "pass":
        return "approved", []
    if result == "needs_verification":
        lic = _last(records, "lookup_license", asset_id=aid)
        if lic is None or not lic.ok:
            return "needs_verification", reasons
        if lic.result.get("status") == "valid":
            return "approved", []
        return "risk_blocked", reasons + [f"授权补查结果：{lic.result.get('status')}"]
    return ("missing_info" if result == "missing_info" else "risk_blocked"), reasons


def known_free(records: list[ToolRecord]) -> set[tuple[str, str, str]]:
    free = set()
    for r in records:
        if r.tool == "query_slots" and r.ok:
            ch, date = r.result["channel"], r.result["date"]
            if r.result.get("available"):
                free.add((ch, date, r.result["requested_time"]))
            free.update((ch, date, t) for t in r.result.get("free_slots_nearby", []))
    return free


def _norm(slot) -> str | None:
    slot = (slot or "").strip()
    return slot or None


def guard(args: dict, records: list[ToolRecord], payload: dict) -> tuple[dict, list[str]]:
    if not isinstance(args.get("items"), list):
        raise ValueError("finish.items 必须是数组")
    # 完整性与格式不合格时退回给模型继续处理（ReActAgent 会把错误作为观察返回）
    unchecked = [it["asset_id"] for it in payload.get("items", [])
                 if not any(r.tool == "check_rules" and r.arguments.get("asset_id") == it["asset_id"] for r in records)
                 and review_truth(records, it["asset_id"])[0] != "not_found"]
    if unchecked:
        raise ValueError(f"以下素材还没有做规则检查，不能结束：{unchecked}。请继续处理。")
    bad = [it.get("asset_id") for it in args["items"] if isinstance(it, dict) and _norm(it.get("suggested_slot"))
           and not SLOT.match(_norm(it.get("suggested_slot")))]
    if bad:
        raise ValueError(f"{bad} 的 suggested_slot 必须是单个时段，格式 YYYY-MM-DD HH:MM；待选多个时段时请写进 confirmation_question。")
    fixes: list[str] = []
    model_items = {it.get("asset_id"): it for it in args["items"] if isinstance(it, dict)}
    confirmations = payload.get("user_confirmations", {})
    free = known_free(records)
    last_save = next((r for r in reversed(records) if r.tool == "save_draft"), None)
    ok_save = next((r for r in reversed(records) if r.tool == "save_draft" and r.ok), None)
    saved_slots = {i["asset_id"]: i["slot"] for i in (ok_save.result["items"] if ok_save else [])}

    items = []
    for req in payload.get("items", []):
        aid = req["asset_id"]
        m = model_items.get(aid)
        if m is None:
            fixes.append(f"{aid}：模型未给出结论，按工具事实补全")
            m = {}
        truth, truth_reasons = review_truth(records, aid)
        status = m.get("review_status") or truth
        if status == "approved" and truth != "approved":
            fixes.append(f"{aid}：模型标为 approved，但工具结果为 {truth}")
            status = truth
        reasons = list(m.get("risk_reasons") or [])
        if status != "approved" and not reasons:
            reasons = truth_reasons or ["审核未完成"]
        requested_slot = f"{req['date']} {req['time']}"
        fixed = req.get("time_rule") == "fixed"
        suggested = _norm(m.get("suggested_slot"))
        slot_status = m.get("slot_status") or "not_scheduled"
        if not suggested and status == "approved":
            # 模型在 save_draft 里已选定时段、保存因工具故障失败、finish 又漏填时，按它自己的动作补回
            tried = [i for r in records if r.tool == "save_draft" and not r.ok and r.result.get("error_type") == "tool_failure"
                     for i in r.arguments.get("items", []) if isinstance(i, dict) and i.get("asset_id") == aid]
            if tried and tried[-1].get("date") and tried[-1].get("time"):
                suggested = f"{tried[-1]['date']} {tried[-1]['time']}"
                fixes.append(f"{aid}：finish 漏填时段，按保存尝试补回 {suggested}")

        if suggested and status != "approved":
            fixes.append(f"{aid}：审核未通过，撤销建议时段 {suggested}")
            suggested = None
        if suggested:
            date, _, time = suggested.partition(" ")
            if (req["channel"], date, time) not in free and saved_slots.get(aid) != suggested:
                fixes.append(f"{aid}：建议时段 {suggested} 未经 query_slots 确认空闲，已撤销")
                suggested = None
        if suggested and fixed and suggested != requested_slot and confirmations.get(aid) != suggested:
            fixes.append(f"{aid}：{requested_slot} 是硬性要求，未经同意不得改为 {suggested}")
            suggested, slot_status = None, "conflict_fixed"

        if suggested is None:
            # 不排期时的原因只按查询事实给出，不沿用模型的说法
            q = _last(records, "query_slots", channel=req["channel"], date=req["date"], time=req["time"])
            q = q if q and q.ok else None
            if status != "approved" or q is None:
                slot_status = "not_scheduled"
            elif fixed and not q.result.get("available"):
                slot_status = "conflict_fixed"
            elif q.result.get("available") or q.result.get("free_slots_nearby"):
                slot_status = "not_scheduled"  # 有空闲时段，但模型没有选
            else:
                slot_status = "no_free_slot"
        else:
            slot_status = "as_requested" if suggested == requested_slot else "alternative_proposed"

        user_ok = suggested is not None and confirmations.get(aid) == suggested
        must_confirm = status != "approved" or suggested is None or (suggested != requested_slot and not user_ok)
        if must_confirm and not m.get("needs_confirmation"):
            if m:
                fixes.append(f"{aid}：存在待确认事项，needs_confirmation 改为 true")
        question = m.get("confirmation_question") or ""
        if must_confirm and not question:
            question = (f"{requested_slot} 不可用，是否同意改为 {suggested}？" if suggested and suggested != requested_slot
                        else "请处理：" + "；".join(reasons or ["时段冲突"]))
        items.append({
            "asset_id": aid,
            "review_status": status,
            "risk_reasons": reasons,
            "requested_slot": requested_slot,
            "suggested_slot": suggested,
            "slot_status": slot_status,
            "needs_confirmation": bool(must_confirm or m.get("needs_confirmation")),
            "confirmation_question": question if (must_confirm or m.get("needs_confirmation")) else "",
        })

    claimed = args.get("draft") or {}
    if ok_save:
        draft = {"saved": True, "draft_id": ok_save.result["draft_id"], "status": "draft",
                 "version": ok_save.result["version"], "deduplicated": bool(ok_save.result.get("deduplicated")),
                 "error": None}
        for it in items:
            if it["suggested_slot"] != saved_slots.get(it["asset_id"]):
                fixes.append(f"{it['asset_id']}：最终建议 {it['suggested_slot']} 与草稿内容 {saved_slots.get(it['asset_id'])} 不一致")
                it["needs_confirmation"] = True
    else:
        error = None
        if last_save:
            error = last_save.result.get("error") or "; ".join(last_save.result.get("errors", []))
        draft = {"saved": False, "draft_id": None, "status": None, "version": None, "deduplicated": False,
                 "error": error or "未调用 save_draft"}
    if bool(claimed.get("saved")) != draft["saved"]:
        fixes.append(f"草稿保存状态以工具结果为准：saved={draft['saved']}")

    schedulable = [it for it in items if it["suggested_slot"]]
    if schedulable and not draft["saved"]:
        status = "save_failed"
    elif not schedulable:
        status = "blocked"
    elif any(it["needs_confirmation"] for it in items):
        status = "needs_confirmation"
    else:
        status = "completed"
    if args.get("task_status") != status:
        fixes.append(f"task_status 由 {args.get('task_status')} 校正为 {status}")

    summary = str(args.get("summary") or "")
    if PUBLISH_CLAIM.search(summary):
        fixes.append("summary 含“已发布”类表述，已改写（系统只保存草稿）")
        summary = PUBLISH_CLAIM.sub("已生成草稿（未发布）", summary)
    if not draft["saved"] and re.search(r"保存成功|已保存", summary) and "失败" not in summary:
        fixes.append("summary 声称已保存，但保存未成功")
        summary = "草稿保存失败：" + summary
    return {"items": items, "draft": draft, "task_status": status, "summary": summary,
            "publish_status": "not_published"}, fixes


def on_incomplete(records: list[ToolRecord], payload: dict, reason: str) -> dict:
    ok_save = next((r for r in reversed(records) if r.tool == "save_draft" and r.ok), None)
    return {
        "items": [{"asset_id": it["asset_id"], "review_status": review_truth(records, it["asset_id"])[0]}
                  for it in payload.get("items", [])],
        "draft": {"saved": bool(ok_save), "draft_id": ok_save.result["draft_id"] if ok_save else None},
        "summary": f"未完成：{reason}；已执行 {len(records)} 次工具调用，未完成部分需重新提交。",
        "publish_status": "not_published",
    }
