# 验收结果（openai-compat:glm-4-flash）

检查通过 36/50。逐条 Trace 见 `examples/runs/glm-4-flash-r3/`。

| 用例 | 覆盖验收点 | 结束状态 | 检查通过 |
|---|---|---|---|
| c01_normal | 正常排期 | completed | 5/5 |
| c02_missing_info | 素材信息缺失 | blocked | 6/6 |
| c03_rule_risk | 规则风险 | blocked | 3/6 |
| c04_slot_conflict | 时段冲突 | blocked | 3/7 |
| c05_fixed_time_conflict | 时段冲突、确认边界 | blocked | 3/4 |
| c06_duplicate_submit | 重复提交 | save_failed → save_failed | 1/4 |
| c07_save_failure | 保存失败、工具失败 | blocked | 4/5 |
| c08_user_confirms_alternative | 时段冲突、确认边界、重复提交 | blocked → completed | 2/4 |
| c09_conflict_shifted | 时段冲突 | needs_confirmation | 6/6 |
| c10_step_limit | 步数上限 | incomplete | 3/3 |

## 未通过的检查

- c03_rule_risk：M05 补查有效后排期（None）
- c03_rule_risk：草稿只含 M05（set()）
- c03_rule_risk：状态 needs_confirmation（有待处理素材）（blocked）
- c04_slot_conflict：建议时段为替代空闲时段（）
- c04_slot_conflict：建议为最近空闲的 19:00（参考实例）（None）
- c04_slot_conflict：草稿中该项 confirmed=false（[]）
- c04_slot_conflict：状态 needs_confirmation（blocked）
- c05_fixed_time_conflict：硬性时间未被改动（None no_free_slot）
- c06_duplicate_submit：两次都保存成功（）
- c06_duplicate_submit：存储中只有 1 份草稿、版本 1（drafts=0）
- c06_duplicate_submit：第二次标记 deduplicated（）
- c07_save_failure：状态 save_failed（blocked）
- c08_user_confirms_alternative：首次运行待确认（blocked）
- c08_user_confirms_alternative：仍只有 1 份草稿，版本更新为 2 且已确认（[{'asset_id': 'M01', 'channel': 'douyin', 'slot': '2026-11-03 19:00', 'requested_slot': '2026-11-03 18:00', 'confirmed': True}]）
