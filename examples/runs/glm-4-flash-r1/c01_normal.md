# c01_normal：正常排期：无风险素材、要求时段空闲（运行 1/1）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`completed`（model_finished）
- 决策轮数：7；业务工具调用：4

## 输入

```json
{
  "request_id": "REQ-C01",
  "items": [
    {
      "asset_id": "M02",
      "channel": "xiaohongshu",
      "date": "2026-11-03",
      "time": "10:00",
      "time_rule": "flexible"
    }
  ]
}
```

## 执行记录

| 步骤 | 动作 | 参数 | 返回摘要 | 决策依据 |
|---|---|---|---|---|
| 1 | `read_asset` | {"asset_id": "M02"} | {"found": true, "asset": {"asset_id": "M02", "title": "门店探访 vlog", "type": "video", "caption": "周末去了新开的城市旗舰店", "cover": "covers/m02.jpg", "copyright": "owned", "music": {"track": "Lofi Morning", "license": "verified"}, "submitter": "运营-周"}, "ok": true} | 读取素材元数据 |
| 2 | `check_rules` | {"asset_id": "M02"} | {"found": true, "asset_id": "M02", "result": "pass", "issues": [], "ok": true} | 检查素材审核规则 |
| 3 | no_tool_call | — | 素材审核状态：通过 风险原因：无 建议时段：2026-11-03 10:00 待确认项：无 | — |
| 4 | `query_slots` | {"channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"} | {"channel": "xiaohongshu", "date": "2026-11-03", "requested_time": "10:00", "available": true, "occupied_by": null, "free_slots_nearby": ["11:00", "09:00", "13:00", "14:00"], "ok": true} | 查询指定时段是否空闲 |
| 5 | no_tool_call | — | 素材审核状态：通过 风险原因：无 建议时段：2026-11-03 10:00 待确认项：无 排期草稿：已生成，包含素材ID为M02的排期信息。 | — |
| 6 | `save_draft` | {"items": [{"asset_id": "M02", "channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"}]} | {"draft_id": "DRAFT-679aec8b", "status": "draft", "version": 1, "deduplicated": false, "items": [{"asset_id": "M02", "channel": "xiaohongshu", "slot": "2026-11-03 10:00", "requested_slot": "2026-11-03 10:00", "confirmed": true}], "note": "已保存为草稿；未发布", "ok": true} | 保存排期草稿 |
| 7 | `finish` | status=completed | 护栏校正 0 处 | 任务完成，提交结构化结果 |

## 最终输出

```json
{
  "items": [
    {
      "asset_id": "M02",
      "review_status": "approved",
      "risk_reasons": [],
      "requested_slot": "2026-11-03 10:00",
      "suggested_slot": "2026-11-03 10:00",
      "slot_status": "as_requested",
      "needs_confirmation": false,
      "confirmation_question": ""
    }
  ],
  "draft": {
    "saved": true,
    "draft_id": "DRAFT-679aec8b",
    "status": "draft",
    "version": 1,
    "deduplicated": false,
    "error": null
  },
  "task_status": "completed",
  "summary": "素材审核通过，已成功排期",
  "publish_status": "not_published"
}
```
