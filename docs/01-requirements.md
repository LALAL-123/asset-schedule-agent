# 01 需求

## 用户

内容团队的运营/排期负责人。手上有一批待发布素材和期望发布时间，需要知道：哪些能发、哪些要改、什么时候发、哪些还要人拍板。

## 目标

把“素材 + 期望时段”变成一份**无冲突、可确认**的排期草稿，并把每项素材的结论讲清楚：

| 输出字段 | 含义 |
|---|---|
| `review_status` | approved / needs_verification / missing_info / risk_blocked / not_found / unchecked |
| `risk_reasons` | 命中的规则与原因（如“含广告极限词：全网最低”） |
| `suggested_slot` | 建议时段；不排期为空 |
| `slot_status` | as_requested / alternative_proposed / conflict_fixed / no_free_slot / not_scheduled |
| `needs_confirmation` + `confirmation_question` | 需要用户确认或补充的事项 |
| `draft` | 是否保存、草稿 ID、版本、是否去重、失败原因 |
| `task_status` | completed / needs_confirmation / blocked / save_failed / incomplete |

## 输入

```json
{"request_id": "REQ-C04",
 "items": [{"asset_id": "M01", "channel": "douyin", "date": "2026-11-03", "time": "18:00", "time_rule": "flexible"}],
 "user_confirmations": {"M01": "2026-11-03 19:00"}}
```

- `time_rule`：`fixed` 为硬性时间，未经用户同意不能改；`flexible` 可在同日调整，但调整后必须待确认。
- `user_confirmations`：用户已同意的替代时段（第二轮提交时带上）。
- 材料：`data/assets.json`（素材元数据）、`data/rules.json`（R01–R04）、`data/licenses.json`（音乐授权库）、`data/schedule.json`（已有排期）。

## 范围

做：审核、补查、时段查询与替代、请求确认、草稿保存（幂等）、失败与上限的明确状态。

不做：真实发布、跨日/跨渠道调度优化、多人协作锁、界面。

## 成功标准

1. 六个必须验收点（正常排期、信息缺失、规则风险、时段冲突、重复提交、保存失败）各有用例且检查全部通过。
2. 关键缺陷为零：
   - 不出现“已发布”类表述，`publish_status` 恒为 `not_published`；
   - 不虚报保存成功：`draft.saved` 只来自 `save_draft` 的成功返回；
   - 不擅改硬性时间；改过的时段未经确认不得标为已确认；
   - 审核未通过的素材不进草稿。
3. 同一请求重复提交，存储中只有一份草稿。
4. 达到步数或调用上限时返回 `incomplete` 和原因。
5. 至少两条执行路径能体现动作随工具结果改变（时段空闲 vs 占用；授权有效 vs 过期）。
