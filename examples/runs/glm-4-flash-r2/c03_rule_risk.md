# c03_rule_risk：规则风险：极限词阻断；未核验配乐补查后一通过一阻断（运行 1/1）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`needs_confirmation`（model_finished）
- 决策轮数：14；业务工具调用：11

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
| 1 | `read_asset` | {"asset_id": "M04"} | {"found": true, "asset": {"asset_id": "M04", "title": "双 11 预热", "type": "video", "caption": "全网最低价，史上最强性能，错过再等一年", "cover": "covers/m04.jpg", "copyright": "owned", "music": {"track": "原创配乐-02", "license": "owned"}, "submitter": "运营-吴"}, "ok": true} | Initial asset read request for M04 |
| 2 | `check_rules` | {"asset_id": "M04"} | {"found": true, "asset_id": "M04", "result": "risk", "issues": [{"rule_id": "R02", "level": "risk", "detail": "含广告极限词：全网最低、最低价、史上最强、最强"}], "ok": true} | Checking rules for asset M04 |
| 3 | `lookup_license` | {"asset_id": "M04"} | {"asset_id": "M04", "track": "原创配乐-02", "status": "not_found", "ok": true} | Checking license for music track in asset M04 |
| 4 | no_tool_call | — | 素材 M04 的审核状态为风险 blocked，原因包括： - 规则 R02：含广告极限词，如“全网最低”、“最低价”、“史上最强”、“最强”。 - 音乐授权问题：原创配乐-02 在授权库中未找到。  建议时段和待确认项：由于存在风险，无法排期。需要提交者运营-吴补充或修改素材信息。 | — |
| 5 | `read_asset` | {"asset_id": "M05"} | {"found": true, "asset": {"asset_id": "M05", "title": "夜景拍摄教程", "type": "video", "caption": "三步拍出干净的城市夜景", "cover": "covers/m05.jpg", "copyright": "owned", "music": {"track": "City Lights", "license": "unverified"}, "submitter": "运营-周"}, "ok": true} | Initial asset read request for M05 |
| 6 | `check_rules` | {"asset_id": "M05"} | {"found": true, "asset_id": "M05", "result": "needs_verification", "issues": [{"rule_id": "R04", "level": "needs_verification", "detail": "配乐《City Lights》授权未核验，可用 lookup_license 补查"}], "ok": true} | Checking rules for asset M05 |
| 7 | `lookup_license` | {"asset_id": "M05"} | {"asset_id": "M05", "track": "City Lights", "status": "valid", "licensor": "合成音乐库A", "expires": "2027-06-30", "ok": true} | Checking license for music track in asset M05 |
| 8 | `query_slots` | {"channel": "douyin", "date": "2026-11-04", "time": "20:00"} | {"channel": "douyin", "date": "2026-11-04", "requested_time": "20:00", "available": true, "occupied_by": null, "free_slots_nearby": ["21:00", "19:00", "22:00", "18:00"], "ok": true} | Checking availability for asset M05 |
| 9 | `save_draft` | {"items": [{"asset_id": "M05", "channel": "douyin", "date": "2026-11-04", "time": "20:00"}]} | {"draft_id": "DRAFT-82fc8ad9", "status": "draft", "version": 1, "deduplicated": false, "items": [{"asset_id": "M05", "channel": "douyin", "slot": "2026-11-04 20:00", "requested_slot": "2026-11-04 20:00", "confirmed": true}], "note": "已保存为草稿；未发布", "ok": true} | Saving draft for asset M05 |
| 10 | `read_asset` | {"asset_id": "M06"} | {"found": true, "asset": {"asset_id": "M06", "title": "海边旅行混剪", "type": "video", "caption": "秋天的海边，风刚刚好", "cover": "covers/m06.jpg", "copyright": "licensed", "music": {"track": "Summer Hit", "license": "unverified"}, "submitter": "运营-吴"}, "ok": true} | Initial asset read request for M06 |
| 11 | `check_rules` | {"asset_id": "M06"} | {"found": true, "asset_id": "M06", "result": "needs_verification", "issues": [{"rule_id": "R04", "level": "needs_verification", "detail": "配乐《Summer Hit》授权未核验，可用 lookup_license 补查"}], "ok": true} | Checking rules for asset M06 |
| 12 | `lookup_license` | {"asset_id": "M06"} | {"asset_id": "M06", "track": "Summer Hit", "status": "expired", "licensor": "合成音乐库B", "expires": "2026-09-30", "ok": true} | Checking license for music track in asset M06 |
| 13 | no_tool_call | — | 素材 M06 的审核状态为 needs_verification，原因包括： - 配乐《Summer Hit》授权已过期。  建议时段和待确认项：由于配乐授权过期，无法排期。需要提交者运营-吴更新配乐授权信息。 | — |
| 14 | `finish` | status=needs_confirmation | 护栏校正 3 处 | Finalizing task for request REQ-C03 |

## 护栏校正

- M04：存在待确认事项，needs_confirmation 改为 true
- M06：存在待确认事项，needs_confirmation 改为 true
- task_status 由 completed 校正为 needs_confirmation

## 最终输出

```json
{
  "items": [
    {
      "asset_id": "M04",
      "review_status": "risk_blocked",
      "risk_reasons": [
        "含广告极限词：全网最低、最低价、史上最强、最强",
        "音乐授权问题：原创配乐-02 在授权库中未找到"
      ],
      "requested_slot": "2026-11-04 19:00",
      "suggested_slot": null,
      "slot_status": "not_scheduled",
      "needs_confirmation": true,
      "confirmation_question": "请处理：含广告极限词：全网最低、最低价、史上最强、最强；音乐授权问题：原创配乐-02 在授权库中未找到"
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
      "review_status": "needs_verification",
      "risk_reasons": [
        "配乐《Summer Hit》授权已过期"
      ],
      "requested_slot": "2026-11-04 21:00",
      "suggested_slot": null,
      "slot_status": "not_scheduled",
      "needs_confirmation": true,
      "confirmation_question": "请处理：配乐《Summer Hit》授权已过期"
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
  "summary": "素材 M04 和 M06 由于风险或授权问题无法排期，素材 M05 已排期至 2026-11-04 20:00",
  "publish_status": "not_published"
}
```
