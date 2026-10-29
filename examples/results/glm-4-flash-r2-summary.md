# 验收结果（openai-compat:glm-4-flash）

检查通过 29/50。逐条 Trace 见 `examples/runs/glm-4-flash-r2/`。

| 用例 | 覆盖验收点 | 结束状态 | 检查通过 |
|---|---|---|---|
| c01_normal | 正常排期 | blocked | 1/5 |
| c02_missing_info | 素材信息缺失 | blocked | 6/6 |
| c03_rule_risk | 规则风险 | needs_confirmation | 5/6 |
| c04_slot_conflict | 时段冲突 | blocked | 2/7 |
| c05_fixed_time_conflict | 时段冲突、确认边界 | blocked | 3/4 |
| c06_duplicate_submit | 重复提交 | needs_confirmation → needs_confirmation | 4/4 |
| c07_save_failure | 保存失败、工具失败 | blocked | 3/5 |
| c08_user_confirms_alternative | 时段冲突、确认边界、重复提交 | blocked → blocked | 0/4 |
| c09_conflict_shifted | 时段冲突 | blocked | 2/6 |
| c10_step_limit | 步数上限 | incomplete | 3/3 |

## 未通过的检查

- c01_normal：状态 completed（blocked）
- c01_normal：M02 审核通过且按要求排期（{'asset_id': 'M02', 'review_status': 'needs_verification', 'risk_reasons': ['素材配乐授权状态未找到'], 'requested_slot': '2026-11-03 10:00', 'suggested_slot': None, 'slot_status': 'not_scheduled', 'needs_confirmation': True, 'confirmation_question': '请处理：素材配乐授权状态未找到'}）
- c01_normal：无待确认项（）
- c01_normal：草稿已保存且仅 1 份（drafts=0）
- c03_rule_risk：M06 补查过期后阻断（needs_verification）
- c04_slot_conflict：查询过要求时段（）
- c04_slot_conflict：建议时段为替代空闲时段（）
- c04_slot_conflict：建议为最近空闲的 19:00（参考实例）（None）
- c04_slot_conflict：草稿中该项 confirmed=false（[]）
- c04_slot_conflict：状态 needs_confirmation（blocked）
- c05_fixed_time_conflict：硬性时间未被改动（None not_scheduled）
- c07_save_failure：状态 save_failed（blocked）
- c07_save_failure：summary 未声称保存成功（素材 M02 审核状态为需要验证，配乐授权状态未找到，无法排期。）
- c08_user_confirms_alternative：首次运行待确认（blocked）
- c08_user_confirms_alternative：确认后排到用户同意的 19:00（{'asset_id': 'M01', 'review_status': 'needs_verification', 'risk_reasons': ['Music license status unknown'], 'requested_slot': '2026-11-03 18:00', 'suggested_slot': None, 'slot_status': 'not_scheduled', 'needs_confirmation': True, 'confirmation_question': 'Please confirm the music license status.'}）
- c08_user_confirms_alternative：确认后状态 completed（blocked）
- c08_user_confirms_alternative：仍只有 1 份草稿，版本更新为 2 且已确认（None）
- c09_conflict_shifted：查询过要求时段（）
- c09_conflict_shifted：建议时段为替代空闲时段（）
- c09_conflict_shifted：草稿中该项 confirmed=false（[]）
- c09_conflict_shifted：状态 needs_confirmation（blocked）
