# 验收结果（mock:scripted-policy）

检查通过 50/50。逐条 Trace 见 `examples/runs/mock/`。

| 用例 | 覆盖验收点 | 结束状态 | 检查通过 |
|---|---|---|---|
| c01_normal | 正常排期 | completed | 5/5 |
| c02_missing_info | 素材信息缺失 | blocked | 6/6 |
| c03_rule_risk | 规则风险 | needs_confirmation | 6/6 |
| c04_slot_conflict | 时段冲突 | needs_confirmation | 7/7 |
| c05_fixed_time_conflict | 时段冲突、确认边界 | blocked | 4/4 |
| c06_duplicate_submit | 重复提交 | needs_confirmation → needs_confirmation | 4/4 |
| c07_save_failure | 保存失败、工具失败 | save_failed | 5/5 |
| c08_user_confirms_alternative | 时段冲突、确认边界、重复提交 | needs_confirmation → completed | 4/4 |
| c09_conflict_shifted | 时段冲突 | needs_confirmation | 6/6 |
| c10_step_limit | 步数上限 | incomplete | 3/3 |

## 未通过的检查

无
