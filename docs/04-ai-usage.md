# 04 AI 使用说明

## 使用的工具

- Claude Code（模型 Claude Opus 5.5），在本地仓库中生成代码、数据、用例与文档，运行测试与评估。
- 智谱 GLM-4-Flash（免费版）：作为智能体运行时的决策模型，用于真实模型评估，不参与写代码。

## AI 生成的内容

| 部分 | 内容 |
|---|---|
| `src/core/` | ReAct 循环、OpenAI 兼容接入、离线 Mock 适配、工具注册与故障注入、Trace 输出、用例运行 |
| `src/domain/` | 五个业务工具、系统提示词、结束护栏、Mock 策略、验收检查 |
| `data/`、`examples/cases/` | 合成素材、规则、授权库、排期与 10 个用例 |
| `tests/` | 内核、业务、验收测试 |
| `docs/`、`README.md` | 初稿 |

## 本人的修改与决策

本人没有直接改写代码或提示词，所做的是以下决策：

- 让 AI 把四道题都实现出来，按真实模型结果再选题；根据评估对比选定提交题 2，本题作为对照一并公开。
- 选用免费、OpenAI 兼容的智谱 GLM-4-Flash 作为真实模型，自行申请 API Key，只放在本地 `.env`（已被 `.gitignore` 排除）。
- 要求在真实模型上多轮评估，并在文档中如实报告每轮结果与未通过项，不为过检查而改标准。
- 四个仓库均公开发布；通过 GitHub Desktop 推送，并在 GitHub 上统一改为英文仓库名。

## 开发中发现并修正的问题

以下问题由 AI 在阅读测试输出和真实模型 Trace 时发现并修正：

| 问题 | 修正 |
|---|---|
| GLM-4-Flash 常把工具调用写成文本，循环拿不到调用 | 内核只在文本写明工具名且紧跟 JSON 参数时恢复为调用，并在 Trace 中标注 |
| 某次结束结果缺字段时，检查抛异常导致整个评估中断 | 检查出错记为一条未通过的检查 |
| 第 1 轮模型只审了第一项素材就结束 | 仍有素材未做规则检查时，护栏拒绝结束并把原因退回模型 |
| `suggested_slot` 写成“19:00, 16:00”这类多个时段 | 格式不合法的结果同样退回，备选时段写进确认问题 |
| 保存被占用的时段失败后，模型不知道该换哪个 | 保存失败的错误里直接列出当日空闲时段 |
| 合成数据自相矛盾：素材写“已核验”，授权库查不到该曲目；自有配乐补查也返回 not_found，模型据此阻断 | 授权库补上曲目，自有或无配乐返回 not_required |
| 护栏把“有空闲但模型没选”写成 no_free_slot，硬性时间被占也未标 conflict_fixed；保存遇故障后漏填时段被算成 blocked | 不排期的原因只按查询结果给出；按模型在保存中选定的时段补回，状态为 save_failed |
| 测试输出里带有本机用户路径 | 生成 `examples/results/pytest.txt` 时脱敏 |

## 验证方式

1. `python -m pytest -q`：全部通过（见 [examples/results/pytest.txt](../examples/results/pytest.txt)）。
2. `python -m src.cli eval --llm mock`：50/50 项检查通过（见 [examples/results/mock-summary.md](../examples/results/mock-summary.md)）。
3. 逐份阅读 `examples/runs/mock/*.md`，核对每步参数、返回、决策依据与最终结论一致。
4. 真实模型：GLM-4-Flash 三轮，31/50 → 29/50 → 36/50；逐条阅读未通过用例的 Trace，归因写在 [03-evaluation.md](03-evaluation.md)。
