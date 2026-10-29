# c02_missing_info：素材信息缺失 + 素材 ID 不存在（运行 1/1）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`blocked`（model_finished）
- 决策轮数：4；业务工具调用：3

## 输入

```json
{
  "request_id": "REQ-C02",
  "items": [
    {
      "asset_id": "M03",
      "channel": "douyin",
      "date": "2026-11-04",
      "time": "12:00",
      "time_rule": "flexible"
    },
    {
      "asset_id": "M99",
      "channel": "douyin",
      "date": "2026-11-04",
      "time": "13:00",
      "time_rule": "flexible"
    }
  ]
}
```

## 执行记录

| 步骤 | 动作 | 参数 | 返回摘要 | 决策依据 |
|---|---|---|---|---|
| 1 | `read_asset` | {"asset_id": "M03"} | {"found": true, "asset": {"asset_id": "M03", "title": "用户故事合集", "type": "video", "caption": "三位用户的真实故事", "cover": null, "copyright": null, "music": {"track": "无", "license": "none"}, "submitter": "运营-林"}, "ok": true} | 读取素材 M03 的元数据。 |
| 2 | `check_rules` | {"asset_id": "M03"} | {"found": true, "asset_id": "M03", "result": "missing_info", "issues": [{"rule_id": "R01", "level": "missing_info", "detail": "缺少字段：cover, copyright"}], "ok": true} | 检查素材 M03 的审核规则。 |
| 3 | `read_asset` | {"asset_id": "M99"} | {"found": false, "asset_id": "M99", "message": "素材库中没有该 ID", "ok": true} | 读取素材 M99 的元数据。 |
| 4 | `finish` | status=blocked | 护栏校正 2 处 | 完成素材审核与排期任务。 |

## 护栏校正

- M03：存在待确认事项，needs_confirmation 改为 true
- M99：存在待确认事项，needs_confirmation 改为 true

## 最终输出

```json
{
  "items": [
    {
      "asset_id": "M03",
      "review_status": "missing_info",
      "risk_reasons": [
        "缺少字段：cover, copyright"
      ],
      "requested_slot": "2026-11-04 12:00",
      "suggested_slot": null,
      "slot_status": "not_scheduled",
      "needs_confirmation": true,
      "confirmation_question": "请处理：缺少字段：cover, copyright"
    },
    {
      "asset_id": "M99",
      "review_status": "not_found",
      "risk_reasons": [
        "素材库中没有该 ID"
      ],
      "requested_slot": "2026-11-04 13:00",
      "suggested_slot": null,
      "slot_status": "not_scheduled",
      "needs_confirmation": true,
      "confirmation_question": "请处理：素材库中没有该 ID"
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
  "task_status": "blocked",
  "summary": "素材 M03 缺少必要信息，无法排期；素材 M99 不存在，无法处理。",
  "publish_status": "not_published"
}
```
