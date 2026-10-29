# c06_duplicate_submit：重复提交：同一请求连续提交两次，只产生一份草稿（运行 1/2）

- 模型：`mock:scripted-policy`
- 结束状态：`needs_confirmation`（model_finished）
- 决策轮数：8；业务工具调用：7

## 输入

```json
{
  "request_id": "REQ-C06",
  "items": [
    {
      "asset_id": "M01",
      "channel": "douyin",
      "date": "2026-11-03",
      "time": "18:00",
      "time_rule": "flexible"
    },
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
| 1 | `read_asset` | {"asset_id": "M01"} | {"found": true, "asset": {"asset_id": "M01", "title": "冬季新品开箱", "type": "video", "caption": "带你看看今年冬季新品的三个细节", "cover": "covers/m01.jpg", "copyright": "owned", "music": {"track": "原创配乐-01", "license": "owned"}, "submitter": "运营-林"}, "ok": true} | M01 尚未读取，先获取元数据 |
| 2 | `check_rules` | {"asset_id": "M01"} | {"found": true, "asset_id": "M01", "result": "pass", "issues": [], "ok": true} | M01 元数据已读取，按 R01–R04 做规则检查 |
| 3 | `query_slots` | {"channel": "douyin", "date": "2026-11-03", "time": "18:00"} | {"channel": "douyin", "date": "2026-11-03", "requested_time": "18:00", "available": false, "occupied_by": "X91", "free_slots_nearby": ["19:00", "16:00", "21:00", "15:00"], "ok": true} | M01 审核通过，查询 2026-11-03 18:00 是否空闲 |
| 4 | `read_asset` | {"asset_id": "M02"} | {"found": true, "asset": {"asset_id": "M02", "title": "门店探访 vlog", "type": "video", "caption": "周末去了新开的城市旗舰店", "cover": "covers/m02.jpg", "copyright": "owned", "music": {"track": "Lofi Morning", "license": "verified"}, "submitter": "运营-周"}, "ok": true} | M02 尚未读取，先获取元数据 |
| 5 | `check_rules` | {"asset_id": "M02"} | {"found": true, "asset_id": "M02", "result": "pass", "issues": [], "ok": true} | M02 元数据已读取，按 R01–R04 做规则检查 |
| 6 | `query_slots` | {"channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"} | {"channel": "xiaohongshu", "date": "2026-11-03", "requested_time": "10:00", "available": true, "occupied_by": null, "free_slots_nearby": ["11:00", "09:00", "13:00", "14:00"], "ok": true} | M02 审核通过，查询 2026-11-03 10:00 是否空闲 |
| 7 | `save_draft` | {"items": [{"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "19:00"}, {"asset_id": "M02", "channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"}]} | {"draft_id": "DRAFT-75f8b53d", "status": "draft", "version": 1, "deduplicated": false, "items": [{"asset_id": "M01", "channel": "douyin", "slot": "2026-11-03 19:00", "requested_slot": "2026-11-03 18:00", "confirmed": false}, {"asset_id": "M02", "channel": "xiaohongshu", "slot": "2026-11-03 10:00", "requested_slot": "2026-11-03 10:00", "confirmed": true}], "n… | 可排期素材已确定，保存为草稿 |
| 8 | `finish` | status=needs_confirmation | 护栏校正 0 处 | 所有素材已有结论，提交结果 |

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
      "needs_confirmation": true,
      "confirmation_question": "2026-11-03 18:00 已被 X91 占用，建议改为 2026-11-03 19:00，是否同意？"
    },
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
    "draft_id": "DRAFT-75f8b53d",
    "status": "draft",
    "version": 1,
    "deduplicated": false,
    "error": null
  },
  "task_status": "needs_confirmation",
  "summary": "排期草稿 DRAFT-75f8b53d 已保存，未发布；待确认 1 项。",
  "publish_status": "not_published"
}
```
