# c08_user_confirms_alternative：确认闭环：先建议 19:00 待确认；用户同意后再次提交，同一草稿更新为已确认（运行 2/2）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`completed`（model_finished）
- 决策轮数：7；业务工具调用：6

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
| 2 | `check_rules` | {"asset_id": "M01"} | {"found": true, "asset_id": "M01", "result": "pass", "issues": [], "ok": true} | 按审核规则检查素材 |
| 3 | `lookup_license` | {"asset_id": "M01"} | {"asset_id": "M01", "track": "原创配乐-01", "status": "not_required", "note": "自有配乐或无配乐，无需外部授权", "ok": true} | 补查素材配乐授权状态 |
| 4 | `query_slots` | {"channel": "douyin", "date": "2026-11-03", "time": "18:00"} | {"channel": "douyin", "date": "2026-11-03", "requested_time": "18:00", "available": false, "occupied_by": "X91", "free_slots_nearby": ["19:00", "16:00", "21:00", "15:00"], "ok": true} | 查询素材时段是否空闲 |
| 5 | `query_slots` | {"channel": "douyin", "date": "2026-11-03", "time": "19:00"} | {"channel": "douyin", "date": "2026-11-03", "requested_time": "19:00", "available": true, "occupied_by": null, "free_slots_nearby": ["21:00", "22:00", "16:00", "15:00"], "ok": true} | 查询素材时段是否空闲 |
| 6 | `save_draft` | {"items": [{"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "19:00"}]} | {"draft_id": "DRAFT-d4806b4c", "status": "draft", "version": 1, "deduplicated": false, "items": [{"asset_id": "M01", "channel": "douyin", "slot": "2026-11-03 19:00", "requested_slot": "2026-11-03 18:00", "confirmed": true}], "note": "已保存为草稿；未发布", "ok": true} | 保存可排期素材草稿 |
| 7 | `finish` | status=completed | 护栏校正 0 处 | 提交最终结构化结果 |

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
    "version": 1,
    "deduplicated": false,
    "error": null
  },
  "task_status": "completed",
  "summary": "素材审核通过，已排期至2026-11-03 19:00",
  "publish_status": "not_published"
}
```
