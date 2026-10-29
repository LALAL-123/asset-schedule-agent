# 04 AI 使用说明

## 使用的工具

- Claude Code（模型 Claude Opus 5.5），在本地仓库中生成代码、数据、用例与文档，并运行测试。

## AI 生成的内容

| 部分 | 内容 |
|---|---|
| `src/core/` | ReAct 循环、OpenAI 兼容接入、离线 Mock 适配、工具注册与故障注入、Trace 输出、用例运行 |
| `src/domain/` | 五个业务工具、系统提示词、结束护栏、Mock 策略、验收检查 |
| `data/`、`examples/cases/` | 合成素材、规则、授权库、排期与 10 个用例 |
| `tests/` | 内核、业务、验收测试 |
| `docs/`、`README.md` | 初稿 |

## 本人的修改与决策

> 以下由本人按实际情况填写。

- 设计决策：
- 修改过的代码/提示词：
- 发现并修正的 AI 错误：

## 验证方式

1. `python -m pytest -q`：全部通过（见 [examples/results/pytest.txt](../examples/results/pytest.txt)）。
2. `python -m src.cli eval --llm mock`：50/50 项检查通过（见 [examples/results/mock-summary.md](../examples/results/mock-summary.md)）。
3. 逐份阅读 `examples/runs/mock/*.md`，核对每步参数、返回、决策依据与最终结论一致。
4. 真实模型：GLM-4-Flash 三轮，31/50 → 29/50 → 36/50；逐条阅读未通过用例的 Trace，归因写在 [03-evaluation.md](03-evaluation.md)。
