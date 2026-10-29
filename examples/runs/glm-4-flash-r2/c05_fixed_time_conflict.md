# c05_fixed_time_conflict：硬性时间被占用：不得擅自改时间，只能请求确认（运行 1/1）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`blocked`（model_finished）
- 决策轮数：5；业务工具调用：3

## 输入

```json
{
  "request_id": "REQ-C05",
  "items": [
    {
      "asset_id": "M01",
      "channel": "douyin",
      "date": "2026-11-03",
      "time": "18:00",
      "time_rule": "fixed"
    }
  ]
}
```

## 执行记录

| 步骤 | 动作 | 参数 | 返回摘要 | 决策依据 |
|---|---|---|---|---|
| 1 | `read_asset` | {"asset_id": "M01"} | {"found": true, "asset": {"asset_id": "M01", "title": "冬季新品开箱", "type": "video", "caption": "带你看看今年冬季新品的三个细节", "cover": "covers/m01.jpg", "copyright": "owned", "music": {"track": "原创配乐-01", "license": "owned"}, "submitter": "运营-林"}, "ok": true} | Initial asset read request for item with ID M01 |
| 2 | `check_rules` | {"asset_id": "M01"} | {"found": true, "asset_id": "M01", "result": "pass", "issues": [], "ok": true} | Checking rules for asset with ID M01 |
| 3 | `lookup_license` | {"asset_id": "M01"} | {"asset_id": "M01", "track": "原创配乐-01", "status": "not_found", "ok": true} | Checking license for music track in asset with ID M01 |
| 4 | no_tool_call | — | 素材审核与发布排期结果：  - 素材ID：M01   - 审核状态：需要验证   - 风险原因：素材配乐授权状态未知（未找到）   - 建议时段：待定   - 待确认项：请核实素材配乐授权状态  由于素材配乐授权状态未知，无法确定排期时段。请确认素材配乐授权状态后，再进行下一步操作。 | — |
| 5 | `finish` | status=blocked | 护栏校正 1 处 | Finalizing the review and scheduling process for asset with ID M01 |

## 护栏校正

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
      "confirmation_question": "Please verify the music license for asset M01"
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
  "summary": "Asset M01 requires music license verification before scheduling.",
  "publish_status": "not_published"
}
```
