# c03_rule_risk：规则风险：极限词阻断；未核验配乐补查后一通过一阻断（运行 1/1）

- 模型：`mock:scripted-policy`
- 结束状态：`needs_confirmation`（model_finished）
- 决策轮数：11；业务工具调用：10

## 输入

```json
{
  "request_id": "REQ-C03",
  "items": [
    {
      "asset_id": "M04",
      "channel": "douyin",
      "date": "2026-11-04",
      "time": "19:00",
      "time_rule": "flexible"
    },
    {
      "asset_id": "M05",
      "channel": "douyin",
      "date": "2026-11-04",
      "time": "20:00",
      "time_rule": "flexible"
    },
    {
      "asset_id": "M06",
      "channel": "xiaohongshu",
      "date": "2026-11-04",
      "time": "21:00",
      "time_rule": "flexible"
    }
  ]
}
```

## 执行记录

| 步骤 | 动作 | 参数 | 返回摘要 | 决策依据 |
|---|---|---|---|---|
| 1 | `read_asset` | {"asset_id": "M04"} | {"found": true, "asset": {"asset_id": "M04", "title": "双 11 预热", "type": "video", "caption": "全网最低价，史上最强性能，错过再等一年", "cover": "covers/m04.jpg", "copyright": "owned", "music": {"track": "原创配乐-02", "license": "owned"}, "submitter": "运营-吴"}, "ok": true} | M04 尚未读取，先获取元数据 |
| 2 | `check_rules` | {"asset_id": "M04"} | {"found": true, "asset_id": "M04", "result": "risk", "issues": [{"rule_id": "R02", "level": "risk", "detail": "含广告极限词：全网最低、最低价、史上最强、最强"}], "ok": true} | M04 元数据已读取，按 R01–R04 做规则检查 |
| 3 | `read_asset` | {"asset_id": "M05"} | {"found": true, "asset": {"asset_id": "M05", "title": "夜景拍摄教程", "type": "video", "caption": "三步拍出干净的城市夜景", "cover": "covers/m05.jpg", "copyright": "owned", "music": {"track": "City Lights", "license": "unverified"}, "submitter": "运营-周"}, "ok": true} | M05 尚未读取，先获取元数据 |
| 4 | `check_rules` | {"asset_id": "M05"} | {"found": true, "asset_id": "M05", "result": "needs_verification", "issues": [{"rule_id": "R04", "level": "needs_verification", "detail": "配乐《City Lights》授权未核验，可用 lookup_license 补查"}], "ok": true} | M05 元数据已读取，按 R01–R04 做规则检查 |
| 5 | `lookup_license` | {"asset_id": "M05"} | {"asset_id": "M05", "track": "City Lights", "status": "valid", "licensor": "合成音乐库A", "expires": "2027-06-30", "ok": true} | M05 配乐授权未核验（R04），补查授权库后再决定 |
| 6 | `query_slots` | {"channel": "douyin", "date": "2026-11-04", "time": "20:00"} | {"channel": "douyin", "date": "2026-11-04", "requested_time": "20:00", "available": true, "occupied_by": null, "free_slots_nearby": ["21:00", "19:00", "22:00", "18:00"], "ok": true} | M05 审核通过，查询 2026-11-04 20:00 是否空闲 |
| 7 | `read_asset` | {"asset_id": "M06"} | {"found": true, "asset": {"asset_id": "M06", "title": "海边旅行混剪", "type": "video", "caption": "秋天的海边，风刚刚好", "cover": "covers/m06.jpg", "copyright": "licensed", "music": {"track": "Summer Hit", "license": "unverified"}, "submitter": "运营-吴"}, "ok": true} | M06 尚未读取，先获取元数据 |
| 8 | `check_rules` | {"asset_id": "M06"} | {"found": true, "asset_id": "M06", "result": "needs_verification", "issues": [{"rule_id": "R04", "level": "needs_verification", "detail": "配乐《Summer Hit》授权未核验，可用 lookup_license 补查"}], "ok": true} | M06 元数据已读取，按 R01–R04 做规则检查 |
| 9 | `lookup_license` | {"asset_id": "M06"} | {"asset_id": "M06", "track": "Summer Hit", "status": "expired", "licensor": "合成音乐库B", "expires": "2026-09-30", "ok": true} | M06 配乐授权未核验（R04），补查授权库后再决定 |
| 10 | `save_draft` | {"items": [{"asset_id": "M05", "channel": "douyin", "date": "2026-11-04", "time": "20:00"}]} | {"draft_id": "DRAFT-82fc8ad9", "status": "draft", "version": 1, "deduplicated": false, "items": [{"asset_id": "M05", "channel": "douyin", "slot": "2026-11-04 20:00", "requested_slot": "2026-11-04 20:00", "confirmed": true}], "note": "已保存为草稿；未发布", "ok": true} | 可排期素材已确定，保存为草稿 |
| 11 | `finish` | status=needs_confirmation | 护栏校正 0 处 | 所有素材已有结论，提交结果 |

## 最终输出

```json
{
  "items": [
    {
      "asset_id": "M04",
      "review_status": "risk_blocked",
      "risk_reasons": [
        "含广告极限词：全网最低、最低价、史上最强、最强"
      ],
      "requested_slot": "2026-11-04 19:00",
      "suggested_slot": null,
      "slot_status": "not_scheduled",
      "needs_confirmation": true,
      "confirmation_question": "请修改 M04 后重新提交"
    },
    {
      "asset_id": "M05",
      "review_status": "approved",
      "risk_reasons": [],
      "requested_slot": "2026-11-04 20:00",
      "suggested_slot": "2026-11-04 20:00",
      "slot_status": "as_requested",
      "needs_confirmation": false,
      "confirmation_question": ""
    },
    {
      "asset_id": "M06",
      "review_status": "risk_blocked",
      "risk_reasons": [
        "配乐《Summer Hit》授权未核验，可用 lookup_license 补查",
        "授权补查：expired"
      ],
      "requested_slot": "2026-11-04 21:00",
      "suggested_slot": null,
      "slot_status": "not_scheduled",
      "needs_confirmation": true,
      "confirmation_question": "M06 配乐授权expired，请更换配乐或补充授权"
    }
  ],
  "draft": {
    "saved": true,
    "draft_id": "DRAFT-82fc8ad9",
    "status": "draft",
    "version": 1,
    "deduplicated": false,
    "error": null
  },
  "task_status": "needs_confirmation",
  "summary": "排期草稿 DRAFT-82fc8ad9 已保存，未发布；待确认 2 项。",
  "publish_status": "not_published"
}
```
