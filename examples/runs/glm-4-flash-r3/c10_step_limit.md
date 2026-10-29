# c10_step_limit：执行上限：3 轮内无法处理完 3 项素材，返回明确未完成（运行 1/1）

- 模型：`openai-compat:glm-4-flash`
- 结束状态：`incomplete`（step_limit_reached）
- 决策轮数：3；业务工具调用：3

## 输入

```json
{
  "request_id": "REQ-C10",
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
| 1 | `read_asset` | {"asset_id": "M04"} | {"found": true, "asset": {"asset_id": "M04", "title": "双 11 预热", "type": "video", "caption": "全网最低价，史上最强性能，错过再等一年", "cover": "covers/m04.jpg", "copyright": "owned", "music": {"track": "原创配乐-02", "license": "owned"}, "submitter": "运营-吴"}, "ok": true} | 开始处理素材 M04 |
| 2 | `check_rules` | {"asset_id": "M04"} | {"found": true, "asset_id": "M04", "result": "risk", "issues": [{"rule_id": "R02", "level": "risk", "detail": "含广告极限词：全网最低、最低价、史上最强、最强"}], "ok": true} | 检查素材 M04 的审核规则 |
| 3 | `lookup_license` | {"asset_id": "M04"} | {"asset_id": "M04", "track": "原创配乐-02", "status": "not_required", "note": "自有配乐或无配乐，无需外部授权", "ok": true} | 补查素材 M04 的配乐授权状态 |
| 3 | **停止** | — | incomplete：step_limit_reached | 达到执行上限或模型服务异常 |

## 最终输出

```json
{
  "items": [
    {
      "asset_id": "M04",
      "review_status": "risk_blocked"
    },
    {
      "asset_id": "M05",
      "review_status": "unchecked"
    },
    {
      "asset_id": "M06",
      "review_status": "unchecked"
    }
  ],
  "draft": {
    "saved": false,
    "draft_id": null
  },
  "summary": "未完成：step_limit_reached；已执行 3 次工具调用，未完成部分需重新提交。",
  "publish_status": "not_published",
  "task_status": "incomplete",
  "stop_reason": "step_limit_reached"
}
```
