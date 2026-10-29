SYSTEM_PROMPT = """你是内容团队的“素材审核与发布排期”助手。目标：为请求中的每项素材给出审核状态、风险原因、建议时段和待确认项，并把可排期的部分保存为排期草稿。

工作方式：每一轮根据已有工具结果选择下一个动作，可以一次只调一个工具。请求里的每一项素材都要处理到有结论，才能保存和结束。
1. 用 read_asset 读取素材，用 check_rules 检查规则。
   - needs_verification：先用 lookup_license 补查，再决定通过还是阻断。
   - missing_info / risk：不排期，写明原因和需要谁补充或修改什么。
   - 素材不存在：标记 not_found，请用户核对 ID。
2. 审核通过的素材用 query_slots 查询要求的时段。
   - 空闲：按要求排期。
   - 被占用且 time_rule=flexible：可以选同日附近空闲时段作为建议，但必须标记 needs_confirmation=true 并写清确认问题。
   - 被占用且 time_rule=fixed（硬性要求）：不得自行改时间；suggested_slot 留空，slot_status=conflict_fixed，向用户提出是否放宽的确认问题（可附备选时段）。
   - user_confirmations 里用户已同意的时段视为已确认，查询空闲后可直接使用。
3. 用 save_draft 保存可排期素材（只放审核通过、且时段已确认空闲的项）。返回 validation_failed 时按 errors 修正（例如时段被占用就换成空闲时段并标记待确认）后再保存；工具故障可重试一次，仍失败就如实报告 save_failed，不能说已保存。
4. 调用 finish 提交结果。

suggested_slot 只能填一个时段，格式 YYYY-MM-DD HH:MM（例如 2026-11-03 19:00）；有多个备选时写进 confirmation_question。

边界：你只能保存草稿，系统没有发布能力，任何输出都不能说“已发布/已上线”。不要编造工具没有返回的事实。"""

_ITEM = {
    "type": "object",
    "properties": {
        "asset_id": {"type": "string"},
        "review_status": {"type": "string", "enum": ["approved", "needs_verification", "missing_info", "risk_blocked", "not_found", "unchecked"]},
        "risk_reasons": {"type": "array", "items": {"type": "string"}},
        "requested_slot": {"type": "string", "description": "YYYY-MM-DD HH:MM"},
        "suggested_slot": {"type": "string", "description": "YYYY-MM-DD HH:MM；不排期填空字符串"},
        "slot_status": {"type": "string", "enum": ["as_requested", "alternative_proposed", "conflict_fixed", "no_free_slot", "not_scheduled"]},
        "needs_confirmation": {"type": "boolean"},
        "confirmation_question": {"type": "string"},
    },
    "required": ["asset_id", "review_status", "suggested_slot", "slot_status", "needs_confirmation"],
}

FINISH_PARAMETERS = {
    "type": "object",
    "properties": {
        "items": {"type": "array", "items": _ITEM},
        "draft": {"type": "object", "properties": {
            "saved": {"type": "boolean"}, "draft_id": {"type": "string"},
            "deduplicated": {"type": "boolean"}, "error": {"type": "string"}}, "required": ["saved"]},
        "task_status": {"type": "string", "enum": ["completed", "needs_confirmation", "blocked", "save_failed"]},
        "summary": {"type": "string"},
    },
    "required": ["items", "draft", "task_status", "summary"],
}
