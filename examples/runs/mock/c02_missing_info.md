# c02_missing_info：素材信息缺失 + 素材 ID 不存在（运行 1/1）

- 模型：`mock:scripted-policy`
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
| 1 | `read_asset` | {"asset_id": "M03"} | {"found": true, "asset": {"asset_id": "M03", "title": "用户故事合集", "type": "video", "caption": "三位用户的真实故事", "cover": null, "copyright": null, "music": {"track": "无", "license": "none"}, "submitter": "运营-林"}, "ok": true} | M03 尚未读取，先获取元数据 |
| 2 | `check_rules` | {"asset_id": "M03"} | {"found": true, "asset_id": "M03", "result": "missing_info", "issues": [{"rule_id": "R01", "level": "missing_info", "detail": "缺少字段：cover, copyright"}], "ok": true} | M03 元数据已读取，按 R01–R04 做规则检查 |
| 3 | `read_asset` | {"asset_id": "M99"} | {"found": false, "asset_id": "M99", "message": "素材库中没有该 ID", "ok": true} | M99 尚未读取，先获取元数据 |
| 4 | `finish` | status=blocked | 护栏校正 0 处 | 所有素材已有结论，提交结果 |

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
      "confirmation_question": "请补充 M03 的：缺少字段：cover, copyright"
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
      "confirmation_question": "请核对素材 ID M99"
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
  "summary": "本次没有可排期素材，详见各项原因与待确认项。",
  "publish_status": "not_published"
}
```
