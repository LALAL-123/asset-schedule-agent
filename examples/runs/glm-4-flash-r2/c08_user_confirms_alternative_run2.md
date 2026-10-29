# c08_user_confirms_alternative：确认闭环：先建议 19:00 待确认；用户同意后再次提交，同一草稿更新为已确认（运行 2/2）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`blocked`（model_finished）
- 决策轮数：5；业务工具调用：3

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
| 1 | `read_asset` | {"asset_id": "M01"} | {"found": true, "asset": {"asset_id": "M01", "title": "冬季新品开箱", "type": "video", "caption": "带你看看今年冬季新品的三个细节", "cover": "covers/m01.jpg", "copyright": "owned", "music": {"track": "原创配乐-01", "license": "owned"}, "submitter": "运营-林"}, "ok": true} | Initial asset read request for item M01 |
| 2 | `check_rules` | {"asset_id": "M01"} | {"found": true, "asset_id": "M01", "result": "pass", "issues": [], "ok": true} | Checking rules for asset M01 |
| 3 | `lookup_license` | {"asset_id": "M01"} | {"asset_id": "M01", "track": "原创配乐-01", "status": "not_found", "ok": true} | Checking license for music track in asset M01 |
| 4 | no_tool_call | — | 素材 M01 的审核状态为：需要验证。风险原因为：配乐授权状态未知。建议时段为：2026-11-03 18:00。待确认项：请确认配乐授权状态。 | — |
| 5 | `finish` | status=blocked | 护栏校正 2 处 | Finalizing the review process for asset M01 |

## 护栏校正

- M01：审核未通过，撤销建议时段 2026-11-03 18:00
- task_status 由 needs_confirmation 校正为 blocked

## 最终输出

```json
{
  "items": [
    {
      "asset_id": "M01",
      "review_status": "needs_verification",
      "risk_reasons": [
        "Music license status unknown"
      ],
      "requested_slot": "2026-11-03 18:00",
      "suggested_slot": null,
      "slot_status": "not_scheduled",
      "needs_confirmation": true,
      "confirmation_question": "Please confirm the music license status."
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
  "summary": "Asset M01 is pending verification for music license status.",
  "publish_status": "not_published"
}
```
