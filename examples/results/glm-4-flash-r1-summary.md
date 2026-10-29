# 验收结果（openai-compat:glm-4-flash）

检查通过 31/50。逐条 Trace 见 `examples/runs/glm-4-flash/`。

| 用例 | 覆盖验收点 | 结束状态 | 检查通过 |
|---|---|---|---|
| c01_normal | 正常排期 | completed | 5/5 |
| c02_missing_info | 素材信息缺失 | blocked | 6/6 |
| c03_rule_risk | 规则风险 | blocked | 1/6 |
| c04_slot_conflict | 时段冲突 | blocked | 3/7 |
| c05_fixed_time_conflict | 时段冲突、确认边界 | blocked | 4/4 |
| c06_duplicate_submit | 重复提交 | save_failed → save_failed | 1/4 |
| c07_save_failure | 保存失败、工具失败 | save_failed | 5/5 |
| c08_user_confirms_alternative | 时段冲突、确认边界、重复提交 | blocked → save_failed | 0/4 |
| c09_conflict_shifted | 时段冲突 | blocked | 3/6 |
| c10_step_limit | 步数上限 | incomplete | 3/3 |

## 未通过的检查

- c03_rule_risk：M05 先补查授权（）
- c03_rule_risk：M05 补查有效后排期（None）
- c03_rule_risk：M06 补查过期后阻断（unchecked）
- c03_rule_risk：草稿只含 M05（set()）
- c03_rule_risk：状态 needs_confirmation（有待处理素材）（blocked）
- c04_slot_conflict：建议时段为替代空闲时段（）
- c04_slot_conflict：建议为最近空闲的 19:00（参考实例）（None）
- c04_slot_conflict：草稿中该项 confirmed=false（[]）
- c04_slot_conflict：状态 needs_confirmation（blocked）
- c06_duplicate_submit：两次都保存成功（）
- c06_duplicate_submit：存储中只有 1 份草稿、版本 1（drafts=0）
- c06_duplicate_submit：第二次标记 deduplicated（）
- c08_user_confirms_alternative：首次运行待确认（blocked）
- c08_user_confirms_alternative：确认后排到用户同意的 19:00（{'asset_id': 'M01', 'review_status': 'approved', 'risk_reasons': [], 'requested_slot': '2026-11-03 18:00', 'suggested_slot': '2026-11-03 15:00', 'slot_status': 'alternative_proposed', 'needs_confirmation': True, 'confirmation_question': '是否选择同日附近的空闲时段进行排期？'}）
- c08_user_confirms_alternative：确认后状态 completed（save_failed）
- c08_user_confirms_alternative：仍只有 1 份草稿，版本更新为 2 且已确认（None）
- c09_conflict_shifted：建议时段为替代空闲时段（）
- c09_conflict_shifted：草稿中该项 confirmed=false（[]）
- c09_conflict_shifted：状态 needs_confirmation（blocked）
