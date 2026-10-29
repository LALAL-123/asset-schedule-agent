"""业务工具（本地函数 + 合成数据）：素材读取、规则检查、授权补查、时段查询、草稿保存。

保存草稿在服务端再次校验审核结果与时段占用，并按 request_id 幂等：
同一请求重复保存只保留一份草稿。这里只存草稿，没有任何发布接口。
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ..core.tools import Tool, ToolError

DATA = Path(__file__).resolve().parents[2] / "data"


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def review(asset: dict, rules: list[dict], licenses: dict | None = None) -> tuple[str, list[dict]]:
    """返回 (pass|needs_verification|missing_info|risk, issues)。传入 licenses 时把未核验音乐也查掉。"""
    issues = []
    for rule in rules:
        rid = rule["rule_id"]
        if rid == "R01":
            missing = [f for f in rule["required_fields"] if not asset.get(f)]
            if missing:
                issues.append({"rule_id": rid, "level": "missing_info", "detail": f"缺少字段：{', '.join(missing)}"})
        elif rid == "R02":
            text = f"{asset.get('title') or ''} {asset.get('caption') or ''}"
            hits = [w for w in rule["banned_terms"] if w in text]
            if hits:
                issues.append({"rule_id": rid, "level": "risk", "detail": f"含广告极限词：{'、'.join(hits)}"})
        elif rid == "R03":
            if asset.get("copyright") and asset["copyright"] not in rule["allowed"]:
                issues.append({"rule_id": rid, "level": "risk", "detail": f"版权状态为 {asset['copyright']}"})
        elif rid == "R04":
            music = asset.get("music") or {}
            lic = music.get("license")
            if lic in rule["needs_verification"]:
                if licenses is None:
                    issues.append({"rule_id": rid, "level": "needs_verification",
                                   "detail": f"配乐《{music.get('track')}》授权未核验，可用 lookup_license 补查"})
                else:
                    status = licenses.get(music.get("track"), {}).get("status", "not_found")
                    if status != "valid":
                        issues.append({"rule_id": rid, "level": "risk", "detail": f"配乐《{music.get('track')}》授权{status}"})
            elif lic not in rule["ok"]:
                issues.append({"rule_id": rid, "level": "risk", "detail": f"配乐授权状态为 {lic}"})
    order = ["pass", "needs_verification", "missing_info", "risk"]
    worst = max((i["level"] for i in issues), key=order.index, default="pass")
    return worst, issues


def request_key(request: dict) -> str:
    key = request.get("request_id")
    if not key:
        body = {k: v for k, v in request.items() if k != "user_confirmations"}
        key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return key


class DraftStore:
    def __init__(self, store_dir: Path):
        self.path = Path(store_dir) / "drafts.json"

    def load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def save(self, drafts: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)


def build_tools(request: dict, env: dict, store_dir: Path) -> list[Tool]:
    assets = {a["asset_id"]: a for a in copy.deepcopy(load_json("assets.json"))}
    for aid, patch in env.get("asset_overrides", {}).items():
        assets.setdefault(aid, {"asset_id": aid}).update(patch)
    rules = load_json("rules.json")["rules"]
    licenses = {**load_json("licenses.json"), **env.get("license_overrides", {})}
    schedule = load_json("schedule.json")
    booked = schedule["booked"] + env.get("extra_booked", [])
    booked = [b for b in booked if f"{b['channel']} {b['date']} {b['time']}" not in set(env.get("unbook", []))]
    slot_times = schedule["slot_times"]
    requested = {it["asset_id"]: it for it in request.get("items", [])}
    confirmations = request.get("user_confirmations", {})
    store = DraftStore(store_dir)
    key = request_key(request)

    def occupied(channel, date, time):
        return next((b["asset_id"] for b in booked
                     if (b["channel"], b["date"], b["time"]) == (channel, date, time)), None)

    def read_asset(asset_id: str):
        asset = assets.get(asset_id)
        if asset is None:
            return {"found": False, "asset_id": asset_id, "message": "素材库中没有该 ID"}
        return {"found": True, "asset": asset}

    def check_rules(asset_id: str):
        asset = assets.get(asset_id)
        if asset is None:
            return {"found": False, "asset_id": asset_id}
        result, issues = review(asset, rules)
        return {"found": True, "asset_id": asset_id, "result": result, "issues": issues}

    def lookup_license(asset_id: str):
        asset = assets.get(asset_id)
        if asset is None:
            return {"found": False, "asset_id": asset_id}
        music = asset.get("music") or {}
        track = music.get("track")
        if music.get("license") in ("owned", "none"):
            return {"asset_id": asset_id, "track": track, "status": "not_required",
                    "note": "自有配乐或无配乐，无需外部授权"}
        entry = licenses.get(track)
        if entry is None:
            return {"asset_id": asset_id, "track": track, "status": "not_found"}
        return {"asset_id": asset_id, "track": track, **entry}

    def query_slots(channel: str, date: str, time: str):
        if time not in slot_times:
            raise ValueError(f"time 须为整点 {slot_times[0]}–{slot_times[-1]}")
        who = occupied(channel, date, time)
        base = slot_times.index(time)
        free = [t for t in slot_times if not occupied(channel, date, t) and t != time]
        # 按与要求时间的距离排序；距离相同优先更晚的时段（不提前抢跑）
        free.sort(key=lambda t: (abs(slot_times.index(t) - base), -slot_times.index(t)))
        return {"channel": channel, "date": date, "requested_time": time, "available": who is None,
                "occupied_by": who, "free_slots_nearby": free[:4]}

    def save_draft(items: list):
        errors, normalized, seen = [], [], set()
        for it in items:
            aid = it.get("asset_id")
            ch, date, time = it.get("channel"), it.get("date"), it.get("time")
            req = requested.get(aid)
            if req is None:
                errors.append(f"{aid} 不在本次请求中")
                continue
            ch = ch or req["channel"]
            asset = assets.get(aid)
            if asset is None:
                errors.append(f"{aid} 不存在")
                continue
            verdict, _ = review(asset, rules, licenses)
            if verdict != "pass":
                errors.append(f"{aid} 审核未通过（{verdict}），不能排期")
            if time not in slot_times:
                errors.append(f"{aid} 时间 {time} 不是可排时段")
            elif occupied(ch, date, time):
                free = [t for t in slot_times if not occupied(ch, date, t)]
                errors.append(f"{aid} 时段 {date} {time} 已被 {occupied(ch, date, time)} 占用；当日空闲时段：{free}")
            if (ch, date, time) in seen:
                errors.append(f"{date} {time} 在草稿内重复")
            seen.add((ch, date, time))
            slot = f"{date} {time}"
            req_slot = f"{req['date']} {req['time']}"
            if req.get("time_rule") == "fixed" and slot != req_slot and confirmations.get(aid) != slot:
                errors.append(f"{aid} 的 {req_slot} 是硬性要求，未经用户同意不能改为 {slot}")
            normalized.append({"asset_id": aid, "channel": ch, "slot": slot,
                               "requested_slot": req_slot,
                               "confirmed": slot == req_slot or confirmations.get(aid) == slot})
        if errors:
            return {"ok": False, "error_type": "validation_failed", "errors": errors}
        normalized.sort(key=lambda x: x["asset_id"])
        digest = hashlib.sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
        drafts = store.load()
        existing = drafts.get(key)
        if existing and existing["content_hash"] == digest:
            return {"draft_id": existing["draft_id"], "status": "draft", "version": existing["version"],
                    "deduplicated": True, "items": existing["items"], "note": "同一请求的相同草稿已存在，未重复创建；未发布"}
        version = existing["version"] + 1 if existing else 1
        draft_id = existing["draft_id"] if existing else "DRAFT-" + hashlib.sha256(key.encode()).hexdigest()[:8]
        drafts[key] = {"draft_id": draft_id, "request_id": key, "status": "draft", "version": version,
                       "content_hash": digest, "items": normalized}
        try:
            store.save(drafts)
        except OSError as exc:
            raise ToolError(f"草稿存储写入失败：{exc}") from exc
        return {"draft_id": draft_id, "status": "draft", "version": version, "deduplicated": False,
                "items": normalized, "note": "已保存为草稿；未发布"}

    obj = {"type": "object"}
    return [
        Tool("read_asset", "读取素材元数据。found=false 表示素材库中没有该 ID。",
             {**obj, "properties": {"asset_id": {"type": "string"}}, "required": ["asset_id"]}, read_asset),
        Tool("check_rules", "按审核规则 R01–R04 检查素材。result: pass / needs_verification(需补查) / missing_info / risk。",
             {**obj, "properties": {"asset_id": {"type": "string"}}, "required": ["asset_id"]}, check_rules),
        Tool("lookup_license", "补查素材配乐在授权库中的状态：valid / expired / not_found；自有配乐或无配乐返回 not_required（无需补查）。",
             {**obj, "properties": {"asset_id": {"type": "string"}}, "required": ["asset_id"]}, lookup_license),
        Tool("query_slots", "查询某渠道某日某整点是否空闲，并返回同日附近空闲时段（按接近程度排序）。",
             {**obj, "properties": {"channel": {"type": "string"}, "date": {"type": "string", "description": "YYYY-MM-DD"},
                                    "time": {"type": "string", "description": "HH:MM 整点"}},
              "required": ["channel", "date", "time"]}, query_slots),
        Tool("save_draft", "把可排期素材保存为排期草稿（不会发布）。同一请求重复保存相同内容不会产生新草稿。"
                           "服务端会复核审核结果、时段占用和硬性时间要求。",
             {**obj, "properties": {"items": {"type": "array", "items": {
                 "type": "object", "properties": {"asset_id": {"type": "string"}, "channel": {"type": "string"},
                                                  "date": {"type": "string"}, "time": {"type": "string"}},
                 "required": ["asset_id", "channel", "date", "time"]}}},
              "required": ["items"]}, save_draft),
    ]
