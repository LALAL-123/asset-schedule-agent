# c07_save_failure：保存失败：草稿存储持续不可用，须明确返回失败（运行 1/1）

- 模型：`mock:scripted-policy`
- 结束状态：`save_failed`（model_finished）
- 决策轮数：6；业务工具调用：5

## 输入

```json
{
  "request_id": "REQ-C07",
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
| 1 | `read_asset` | {"asset_id": "M02"} | {"found": true, "asset": {"asset_id": "M02", "title": "门店探访 vlog", "type": "video", "caption": "周末去了新开的城市旗舰店", "cover": "covers/m02.jpg", "copyright": "owned", "music": {"track": "Lofi Morning", "license": "verified"}, "submitter": "运营-周"}, "ok": true} | M02 尚未读取，先获取元数据 |
| 2 | `check_rules` | {"asset_id": "M02"} | {"found": true, "asset_id": "M02", "result": "pass", "issues": [], "ok": true} | M02 元数据已读取，按 R01–R04 做规则检查 |
| 3 | `query_slots` | {"channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"} | {"channel": "xiaohongshu", "date": "2026-11-03", "requested_time": "10:00", "available": true, "occupied_by": null, "free_slots_nearby": ["11:00", "09:00", "13:00", "14:00"], "ok": true} | M02 审核通过，查询 2026-11-03 10:00 是否空闲 |
| 4 | `save_draft` ✗ | {"items": [{"asset_id": "M02", "channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"}]} | {"ok": false, "error_type": "tool_failure", "error": "草稿存储服务不可用（注入故障）"} | 可排期素材已确定，保存为草稿 |
| 5 | `save_draft` ✗ | {"items": [{"asset_id": "M02", "channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"}]} | {"ok": false, "error_type": "tool_failure", "error": "草稿存储服务不可用（注入故障）"} | 上次保存失败（草稿存储服务不可用（注入故障）），重试一次 |
| 6 | `finish` | status=save_failed | 护栏校正 0 处 | 所有素材已有结论，提交结果 |

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
    "saved": false,
    "draft_id": null,
    "status": null,
    "version": null,
    "deduplicated": false,
    "error": "草稿存储服务不可用（注入故障）"
  },
  "task_status": "save_failed",
  "summary": "排期建议已生成，但草稿保存失败：草稿存储服务不可用（注入故障）。未保存、未发布。",
  "publish_status": "not_published"
}
```
