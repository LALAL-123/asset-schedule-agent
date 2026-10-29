"""离线 Mock 策略：用确定性规则读取工具结果并选择下一步。

用途：无模型时验证循环、工具、护栏与 Trace 能跑通。它本质上是条件分支，
不能证明真实模型的决策能力——真实模型的运行记录见 examples/runs/<模型名>/。
"""
from __future__ import annotations

from ..core.llm import Observation


def _last(obs: list[Observation], tool: str, **match) -> Observation | None:
    for o in reversed(obs):
        if o.tool == tool and all(o.args.get(k) == v for k, v in match.items()):
            return o
    return None


def _count(obs, tool, **match) -> int:
    return sum(1 for o in obs if o.tool == tool and all(o.args.get(k) == v for k, v in match.items()))


def _item(aid, req_slot, status, reasons=(), slot=None, slot_status="not_scheduled", confirm=False, q=""):
    return {"asset_id": aid, "review_status": status, "risk_reasons": list(reasons), "requested_slot": req_slot,
            "suggested_slot": slot or "", "slot_status": slot_status, "needs_confirmation": confirm,
            "confirmation_question": q}


def mock_policy(payload: dict, obs: list[Observation]):
    plan = []
    confirmations = payload.get("user_confirmations", {})
    for it in payload.get("items", []):
        aid, ch, date, time = it["asset_id"], it["channel"], it["date"], it["time"]
        req_slot = f"{date} {time}"

        r = _last(obs, "read_asset", asset_id=aid)
        if r is None:
            return "read_asset", f"{aid} 尚未读取，先获取元数据", {"asset_id": aid}
        if not r.result.get("ok"):
            if _count(obs, "read_asset", asset_id=aid) < 2:
                return "read_asset", f"读取 {aid} 失败（{r.result.get('error')}），重试一次", {"asset_id": aid}
            plan.append(_item(aid, req_slot, "unchecked", [f"素材读取失败：{r.result.get('error')}"], confirm=True,
                              q="素材服务异常，请稍后重新提交"))
            continue
        if not r.result.get("found"):
            plan.append(_item(aid, req_slot, "not_found", ["素材库中没有该 ID"], confirm=True, q=f"请核对素材 ID {aid}"))
            continue

        c = _last(obs, "check_rules", asset_id=aid)
        if c is None:
            return "check_rules", f"{aid} 元数据已读取，按 R01–R04 做规则检查", {"asset_id": aid}
        if not c.result.get("ok"):
            if _count(obs, "check_rules", asset_id=aid) < 2:
                return "check_rules", f"{aid} 规则检查失败（{c.result.get('error')}），重试一次", {"asset_id": aid}
            plan.append(_item(aid, req_slot, "unchecked", ["规则检查服务异常"], confirm=True, q="规则检查未完成，暂不排期"))
            continue
        result = c.result["result"]
        reasons = [i["detail"] for i in c.result["issues"]]
        if result == "needs_verification":
            lic = _last(obs, "lookup_license", asset_id=aid)
            if lic is None:
                return "lookup_license", f"{aid} 配乐授权未核验（R04），补查授权库后再决定", {"asset_id": aid}
            if lic.result.get("status") != "valid":
                plan.append(_item(aid, req_slot, "risk_blocked", reasons + [f"授权补查：{lic.result.get('status')}"],
                                  confirm=True, q=f"{aid} 配乐授权{lic.result.get('status')}，请更换配乐或补充授权"))
                continue
            result = "pass"
        if result == "missing_info":
            plan.append(_item(aid, req_slot, "missing_info", reasons, confirm=True, q=f"请补充 {aid} 的：{'；'.join(reasons)}"))
            continue
        if result == "risk":
            plan.append(_item(aid, req_slot, "risk_blocked", reasons, confirm=True, q=f"请修改 {aid} 后重新提交"))
            continue

        wanted = confirmations.get(aid)
        if wanted and wanted != req_slot:
            wd, wt = wanted.split()
            q2 = _last(obs, "query_slots", channel=ch, date=wd, time=wt)
            if q2 is None:
                return "query_slots", f"用户已同意 {aid} 改到 {wanted}，确认该时段仍空闲", {"channel": ch, "date": wd, "time": wt}
            if q2.result.get("available"):
                plan.append(_item(aid, req_slot, "approved", slot=wanted, slot_status="alternative_proposed"))
                continue
        q = _last(obs, "query_slots", channel=ch, date=date, time=time)
        if q is None:
            return "query_slots", f"{aid} 审核通过，查询 {req_slot} 是否空闲", {"channel": ch, "date": date, "time": time}
        if not q.result.get("ok"):
            plan.append(_item(aid, req_slot, "approved", ["时段查询失败"], confirm=True, q="时段服务异常，请稍后重试"))
            continue
        free = q.result.get("free_slots_nearby", [])
        if q.result["available"]:
            plan.append(_item(aid, req_slot, "approved", slot=req_slot, slot_status="as_requested"))
        elif it.get("time_rule") == "fixed":
            alt = f"，可选 {date} {free[0]}" if free else ""
            plan.append(_item(aid, req_slot, "approved", slot_status="conflict_fixed", confirm=True,
                              q=f"{req_slot} 是硬性时间但已被 {q.result['occupied_by']} 占用{alt}，是否同意调整？"))
        elif free:
            alt = f"{date} {free[0]}"
            plan.append(_item(aid, req_slot, "approved", slot=alt, slot_status="alternative_proposed", confirm=True,
                              q=f"{req_slot} 已被 {q.result['occupied_by']} 占用，建议改为 {alt}，是否同意？"))
        else:
            plan.append(_item(aid, req_slot, "approved", slot_status="no_free_slot", confirm=True, q=f"{date} 当天无空闲时段，请另选日期"))

    schedulable = [p for p in plan if p["suggested_slot"]]
    saves = [o for o in obs if o.tool == "save_draft"]
    ok_save = next((s for s in reversed(saves) if s.result.get("ok")), None)
    if schedulable and ok_save is None:
        last = saves[-1] if saves else None
        if last is None or (len(saves) < 2 and last.result.get("error_type") == "tool_failure"):
            channel = {it["asset_id"]: it["channel"] for it in payload["items"]}
            items = [{"asset_id": p["asset_id"], "channel": channel[p["asset_id"]],
                      "date": p["suggested_slot"].split()[0], "time": p["suggested_slot"].split()[1]} for p in schedulable]
            note = "可排期素材已确定，保存为草稿" if last is None else f"上次保存失败（{last.result.get('error')}），重试一次"
            return "save_draft", note, {"items": items}

    if schedulable and ok_save is None:
        err = saves[-1].result.get("error") or "; ".join(saves[-1].result.get("errors", []))
        draft, status = {"saved": False, "error": err}, "save_failed"
        summary = f"排期建议已生成，但草稿保存失败：{err}。未保存、未发布。"
    elif not schedulable:
        draft, status = {"saved": False, "error": "无可排期素材，未保存"}, "blocked"
        summary = "本次没有可排期素材，详见各项原因与待确认项。"
    else:
        draft = {"saved": True, "draft_id": ok_save.result["draft_id"],
                 "deduplicated": bool(ok_save.result.get("deduplicated"))}
        status = "needs_confirmation" if any(p["needs_confirmation"] for p in plan) else "completed"
        dedup = "（与已有草稿相同，未重复创建）" if draft["deduplicated"] else ""
        summary = f"排期草稿 {draft['draft_id']} 已保存{dedup}，未发布；待确认 {sum(p['needs_confirmation'] for p in plan)} 项。"
    return "finish", "所有素材已有结论，提交结果", {"items": plan, "draft": draft, "task_status": status, "summary": summary}
