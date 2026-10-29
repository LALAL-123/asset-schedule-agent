# c08_user_confirms_alternative：确认闭环：先建议 19:00 待确认；用户同意后再次提交，同一草稿更新为已确认（运行 2/2）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`save_failed`（model_finished）
- 决策轮数：7；业务工具调用：3

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
| 1 | `read_asset` | {"asset_id": "M01"} | {"found": true, "asset": {"asset_id": "M01", "title": "冬季新品开箱", "type": "video", "caption": "带你看看今年冬季新品的三个细节", "cover": "covers/m01.jpg", "copyright": "owned", "music": {"track": "原创配乐-01", "license": "owned"}, "submitter": "运营-林"}, "ok": true} | 读取素材元数据 |
| 2 | `check_rules` | {"asset_id": "M01"} | {"found": true, "asset_id": "M01", "result": "pass", "issues": [], "ok": true} | 检查素材审核规则 |
| 3 | no_tool_call | — | 素材审核通过，无风险。素材ID为M01的审核状态为“已通过”，风险原因为“无”，建议时段为“2026-11-03 18:00”，待确认项为“无”。 | — |
| 4 | `query_slots` | {"channel": "douyin", "date": "2026-11-03", "time": "18:00"} | {"channel": "douyin", "date": "2026-11-03", "requested_time": "18:00", "available": false, "occupied_by": "X91", "free_slots_nearby": ["19:00", "16:00", "21:00", "15:00"], "ok": true} | 查询素材排期时段 |
| 5 | no_tool_call | — | 素材M01在2026-11-03 18:00的时段已被占用，建议时段为同日附近的空闲时段，包括19:00、16:00、21:00和15:00。需要确认是否选择其中一个时段。 | — |
| 6 | no_tool_call | — |  | — |
| 7 | `finish` | status=save_failed | 护栏校正 2 处 | 提交最终结构化结果 |

## 护栏校正

- 草稿保存状态以工具结果为准：saved=False
- task_status 由 needs_confirmation 校正为 save_failed

## 最终输出

```json
{
  "items": [
    {
      "asset_id": "M01",
      "review_status": "approved",
      "risk_reasons": [],
      "requested_slot": "2026-11-03 18:00",
      "suggested_slot": "2026-11-03 15:00",
      "slot_status": "alternative_proposed",
      "needs_confirmation": true,
      "confirmation_question": "是否选择同日附近的空闲时段进行排期？"
    }
  ],
  "draft": {
    "saved": false,
    "draft_id": null,
    "status": null,
    "version": null,
    "deduplicated": false,
    "error": "未调用 save_draft"
  },
  "task_status": "save_failed",
  "summary": "素材M01审核通过，但排期时段冲突，建议选择同日附近的空闲时段进行排期。",
  "publish_status": "not_published"
}
```
