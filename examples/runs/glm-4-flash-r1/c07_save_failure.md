# c07_save_failure：保存失败：草稿存储持续不可用，须明确返回失败（运行 1/1）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`save_failed`（model_finished）
- 决策轮数：10；业务工具调用：5

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
| 1 | `read_asset` | {"asset_id": "M02"} | {"found": true, "asset": {"asset_id": "M02", "title": "门店探访 vlog", "type": "video", "caption": "周末去了新开的城市旗舰店", "cover": "covers/m02.jpg", "copyright": "owned", "music": {"track": "Lofi Morning", "license": "verified"}, "submitter": "运营-周"}, "ok": true} | 读取素材元数据 |
| 2 | `check_rules` | {"asset_id": "M02"} | {"found": true, "asset_id": "M02", "result": "pass", "issues": [], "ok": true} | 检查素材审核规则 |
| 3 | no_tool_call | — | 素材审核状态：通过 风险原因：无 建议时段：2026-11-03 10:00 待确认项：无 | — |
| 4 | `query_slots` | {"channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"} | {"channel": "xiaohongshu", "date": "2026-11-03", "requested_time": "10:00", "available": true, "occupied_by": null, "free_slots_nearby": ["11:00", "09:00", "13:00", "14:00"], "ok": true} | 查询指定时段是否空闲 |
| 5 | no_tool_call | — | 素材审核状态：通过 风险原因：无 建议时段：2026-11-03 10:00 待确认项：无 排期草稿：已生成，包含素材ID为M02的排期信息。 | — |
| 6 | `save_draft` ✗ | {"items": [{"asset_id": "M02", "channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"}]} | {"ok": false, "error_type": "tool_failure", "error": "草稿存储服务不可用（注入故障）"} | 保存排期草稿 |
| 7 | no_tool_call | — | 保存草稿失败，错误原因：草稿存储服务不可用（注入故障）。请稍后再试或联系技术支持。 | — |
| 8 | `save_draft` ✗ | {"items": [{"asset_id": "M02", "channel": "xiaohongshu", "date": "2026-11-03", "time": "10:00"}]} | {"ok": false, "error_type": "tool_failure", "error": "草稿存储服务不可用（注入故障）"} | 重试保存排期草稿 |
| 9 | no_tool_call | — | 保存草稿失败，错误原因：草稿存储服务不可用（注入故障）。请稍后再试或联系技术支持。 | — |
| 10 | `finish` | status=save_failed | 护栏校正 0 处 | 任务完成，所有必要动作已完成，但保存草稿失败 |

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
  "summary": "素材审核通过，已查询到空闲时段，但保存草稿失败",
  "publish_status": "not_published"
}
```
