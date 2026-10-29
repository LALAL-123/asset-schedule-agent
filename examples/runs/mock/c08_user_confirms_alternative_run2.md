# c08_user_confirms_alternative：确认闭环：先建议 19:00 待确认；用户同意后再次提交，同一草稿更新为已确认（运行 2/2）

- 模型：`mock:scripted-policy`
- 结束状态：`completed`（model_finished）
- 决策轮数：5；业务工具调用：4

## 输入

```json
{
  "request_id": "REQ-C08",
  "items": [
    {
      "asset_id": "M01",
      "channel": "douyin",
      "date": "2026-11-03",
      "time": "18:00",
      "time_rule": "flexible"
    }
  ],
  "user_confirmations": {
    "M01": "2026-11-03 19:00"
  }
}
```

## 执行记录

| 步骤 | 动作 | 参数 | 返回摘要 | 决策依据 |
|---|---|---|---|---|
| 1 | `read_asset` | {"asset_id": "M01"} | {"found": true, "asset": {"asset_id": "M01", "title": "冬季新品开箱", "type": "video", "caption": "带你看看今年冬季新品的三个细节", "cover": "covers/m01.jpg", "copyright": "owned", "music": {"track": "原创配乐-01", "license": "owned"}, "submitter": "运营-林"}, "ok": true} | M01 尚未读取，先获取元数据 |
| 2 | `check_rules` | {"asset_id": "M01"} | {"found": true, "asset_id": "M01", "result": "pass", "issues": [], "ok": true} | M01 元数据已读取，按 R01–R04 做规则检查 |
| 3 | `query_slots` | {"channel": "douyin", "date": "2026-11-03", "time": "19:00"} | {"channel": "douyin", "date": "2026-11-03", "requested_time": "19:00", "available": true, "occupied_by": null, "free_slots_nearby": ["21:00", "22:00", "16:00", "15:00"], "ok": true} | 用户已同意 M01 改到 2026-11-03 19:00，确认该时段仍空闲 |
| 4 | `save_draft` | {"items": [{"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "19:00"}]} | {"draft_id": "DRAFT-d4806b4c", "status": "draft", "version": 2, "deduplicated": false, "items": [{"asset_id": "M01", "channel": "douyin", "slot": "2026-11-03 19:00", "requested_slot": "2026-11-03 18:00", "confirmed": true}], "note": "已保存为草稿；未发布", "ok": true} | 可排期素材已确定，保存为草稿 |
| 5 | `finish` | status=completed | 护栏校正 0 处 | 所有素材已有结论，提交结果 |

## 最终输出

```json
{
  "items": [
    {
      "asset_id": "M01",
      "review_status": "approved",
      "risk_reasons": [],
      "requested_slot": "2026-11-03 18:00",
      "suggested_slot": "2026-11-03 19:00",
      "slot_status": "alternative_proposed",
      "needs_confirmation": false,
      "confirmation_question": ""
    }
  ],
  "draft": {
    "saved": true,
    "draft_id": "DRAFT-d4806b4c",
    "status": "draft",
    "version": 2,
    "deduplicated": false,
    "error": null
  },
  "task_status": "completed",
  "summary": "排期草稿 DRAFT-d4806b4c 已保存，未发布；待确认 0 项。",
  "publish_status": "not_published"
}
```
