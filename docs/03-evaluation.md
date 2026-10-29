# 03 评估

## 测试结构

| 层次 | 文件 | 内容 |
|---|---|---|
| 内核 | `tests/test_core.py` | 步数/调用上限、finish 同轮拒绝、未知工具/缺参数/工具异常转观察、故障注入、模型异常、非法 finish 退回 |
| 业务 | `tests/test_domain.py` | 时段查询、授权补查改变结论、草稿幂等与升版本、服务端拒绝风险/占用/改硬性时间、护栏校正 |
| 验收 | `tests/test_domain.py::test_case_acceptance_with_offline_mock` | 10 个用例逐条跑验收检查 |
| 评估 | `python -m src.cli eval --llm mock|openai` | 同一套检查用于 Mock 与真实模型，写出 Trace 与汇总 |

验收检查（`src/domain/checks.py`）只看最终结果、工具调用事实和草稿存储，不绑定某条执行路径，所以真实模型换一种合理顺序也能通过。

## 用例：预期与实际（离线 Mock）

全部结果：[examples/results/mock-summary.md](../examples/results/mock-summary.md)，测试输出：[examples/results/pytest.txt](../examples/results/pytest.txt)。

| 用例 | 预期 | 实际 | Trace |
|---|---|---|---|
| c01 正常排期 | M02 按 10:00 排期，completed，1 份草稿 | 一致，5/5 | [c01](../examples/runs/mock/c01_normal.md) |
| c02 信息缺失 | M03 missing_info（缺 cover、copyright），M99 not_found，均不排期，不保存，blocked | 一致，6/6 | [c02](../examples/runs/mock/c02_missing_info.md) |
| c03 规则风险 | M04 极限词阻断；M05 补查 valid 后排期；M06 补查 expired 后阻断；草稿只含 M05 | 一致，6/6 | [c03](../examples/runs/mock/c03_rule_risk.md) |
| c04 时段冲突（参考实例） | 18:00 被占 → 建议 19:00，待确认，草稿内 confirmed=false，不称已发布 | 一致，7/7 | [c04](../examples/runs/mock/c04_slot_conflict.md) |
| c05 硬性时间冲突 | 不改时间，conflict_fixed，提出确认问题，不进草稿 | 一致，4/4 | [c05](../examples/runs/mock/c05_fixed_time_conflict.md) |
| c06 重复提交 | 两次同一 draft_id，存储 1 份、版本 1，第二次 deduplicated | 一致，4/4 | [run1](../examples/runs/mock/c06_duplicate_submit_run1.md) / [run2](../examples/runs/mock/c06_duplicate_submit_run2.md) |
| c07 保存失败 | 重试后仍失败 → save_failed，saved=false 且有错误原因，存储为空 | 一致，5/5 | [c07](../examples/runs/mock/c07_save_failure.md) |
| c08 确认闭环 | 首次待确认；用户同意 19:00 后 completed，同一草稿升到版本 2 且 confirmed=true | 一致，4/4 | [run1](../examples/runs/mock/c08_user_confirms_alternative_run1.md) / [run2](../examples/runs/mock/c08_user_confirms_alternative_run2.md) |
| c09 更换占用时段 | 19:00 也被占 → 建议改为其他空闲时段（16:00） | 一致，6/6 | [c09](../examples/runs/mock/c09_conflict_shifted.md) |
| c10 步数上限 | 3 轮后 incomplete / step_limit_reached，不保存 | 一致，3/3 | [c10](../examples/runs/mock/c10_step_limit.md) |

Mock 运行中护栏校正次数为 0；护栏的拦截能力由 `test_guard_*` 三个单测验证（虚报保存、未查询时段、改硬性时间、“已发布”表述、风险素材被标 approved）。

## 真实模型

模型：智谱 GLM-4-Flash（免费版，OpenAI 兼容接口，temperature=0）。每轮跑全部 10 个用例（12 次运行），与 Mock 共用同一套检查。

| 轮次 | 代码 | 检查通过 | 护栏校正 | finish 被退回 | 汇总 | Trace |
|---|---|---|---|---|---|---|
| 第 1 轮 | 初版 | 31/50 | 14 | 0 | [r1 汇总](../examples/results/glm-4-flash-r1-summary.md) | [glm-4-flash-r1/](../examples/runs/glm-4-flash-r1/) |
| 第 2 轮 | 按第 1 轮问题修改 | 29/50 | 17 | 0 | [r2 汇总](../examples/results/glm-4-flash-r2-summary.md) | [glm-4-flash-r2/](../examples/runs/glm-4-flash-r2/) |
| 第 3 轮 | 修正授权补查数据 | 36/50 | 14 | 4 | [r3 汇总](../examples/results/glm-4-flash-r3-summary.md) | [glm-4-flash-r3/](../examples/runs/glm-4-flash-r3/) |

### 每轮的问题与修改

| 现象 | 修改（在下一轮运行前完成） |
|---|---|
| 第 1 轮 c03：只处理了第一项素材 M04 就 finish，M05、M06 没审 | 第 2 轮：护栏在仍有素材未做规则检查时拒绝结束，把错误作为观察退回模型 |
| 第 1 轮：`suggested_slot` 写成“19:00, 16:00”这类多个时段 | 第 2 轮：格式不合法的 finish 同样退回，提示把备选写进确认问题 |
| 第 1 轮 c06：保存被占用的 18:00，失败后没有改时段 | 第 2 轮：保存失败的错误里直接列出当日空闲时段 |
| 模型把调用写成文本 | 第 2 轮：内核恢复写明工具名和 JSON 参数的文本调用，Trace 标注 |
| 第 2 轮 c01、c07、c08：M01（自有配乐）、M02（已核验配乐）也去调 `lookup_license`，授权库里没有这两首，返回 not_found，模型据此标为 needs_verification 并阻断 | 第 3 轮：这是合成数据与工具的缺陷——素材写着“已核验”，授权库却查不到。授权库补上 M02 的曲目，自有或无配乐返回 `not_required` |

第 2 轮比第 1 轮低，原因是上表最后一行的数据缺陷在第 2 轮被更频繁地触发（模型更勤于补查），修复后第 3 轮 c01、c09 全部通过。

### 第 3 轮未通过项

| 用例 | 现象 | 归因 |
|---|---|---|
| c03 规则风险 | 被退回两次后补审了 M05、M06（[Trace](../examples/runs/glm-4-flash-r3/c03_rule_risk.md)），但 M05 通过后没有查时段、没保存 | 模型；护栏只拦“未审”，没拦“已通过但未排期” |
| c04 时段冲突（参考实例）、c08 首次 | 查到 18:00 被占、19:00 空闲，模型把 4 个空闲时段都列进确认问题，没有选建议时段，也没保存 | 模型 |
| c05 硬性时间冲突 | 保存被占用的 18:00 失败后直接结束；结果写成 no_free_slot，检查要求 conflict_fixed | 护栏缺陷（见下） |
| c06 重复提交 | 两次运行都用被占用的 18:00 连存两次，错误里已列出空闲时段仍不改 | 模型 |
| c07 保存失败 | 选定 10:00 保存，遇到注入故障后结束，finish 漏填时段，状态被算成 blocked | 护栏缺陷（见下） |

第 3 轮读 Trace 发现护栏自身两处与事实不符，已在第 3 轮之后修正，并补了单测（`test_guard_derives_slot_status_from_query_not_from_model`、`test_guard_keeps_slot_from_failed_save_attempt`）；第 3 轮结果仍按当时代码报告：

1. 模型没给建议时段时，护栏把 slot_status 写成 `no_free_slot`，可查询结果明明有空闲时段；硬性时间被占时也没有标 `conflict_fixed`。现在不排期的原因只按 `query_slots` 的结果给出。
2. 保存因工具故障失败、finish 又漏填时段时，状态算成 blocked。现在按模型自己在 `save_draft` 里选的时段补回，状态为 save_failed。

### 结论

- 三轮输出中没有一次虚报“已保存”或“已发布”：草稿状态始终以 `save_draft` 结果为准，模型自报的状态与事实不符时由护栏改正（三轮合计校正 45 处）。
- “退回 finish”比“事后降级”更有用：第 3 轮 c03 中模型被退回后继续补审，[c08 第二次运行](../examples/runs/glm-4-flash-r3/c08_user_confirms_alternative_run2.md) 在用户确认后查询 19:00 并保存。下一步把“已通过但未查时段”“保存失败后未改时段”也改为退回。
- GLM-4-Flash 的主要短板是读到 validation_failed 后不修正参数（c06）和不肯替用户选建议时段（c04）。前者应在换更强模型后复测；后者可让 `query_slots` 直接返回 `recommended_slot`，把“选最近空闲”变成工具事实。

## 失败与限制

- 离线 Mock 是条件分支，它全部通过只说明流程和检查是闭合的；它不能证明 ReAct 决策质量。
- 检查 `c04` 要求建议 19:00（参考实例给定）；若真实模型选了同样空闲的其他时段，该条会失败，其余条目仍通过——这是有意保留的严格项。
- 未覆盖：工具超时（只模拟返回失败）、模型输出非法 JSON 的真实频率、并发提交同一请求。
- 时段只在同日内找替代，当日全满时返回 `no_free_slot`，不会跨日建议。
