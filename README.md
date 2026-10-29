# 素材审核与发布排期 Agent（题 1）

帮内容团队把一批待发布素材变成**无冲突、可确认的排期草稿**：逐项审核 → 补查存疑项 → 查时段 → 冲突时给替代时段并标记待确认 → 保存草稿。系统没有发布能力，只保存草稿。

原生 Python 实现 ReAct 循环（模型选动作 → 执行工具 → 观察 → 再决策或结束），模型走 OpenAI 兼容接口；另有离线 Mock 入口，用于在无模型时验证流程。

## 评审入口

```bash
pip install -r requirements.txt
python -m pytest -q                                   # 内核 + 业务 + 10 个验收用例（离线）
python -m src.cli eval --llm mock                     # 跑全部用例，写出 Trace 与汇总
python -m src.cli run examples/cases/c04_slot_conflict.json --llm mock --fresh   # 参考实例
```

真实模型（任一 OpenAI 兼容服务；本仓库结果用智谱 GLM-4-Flash 免费版）：

```bash
cp .env.example .env        # 填 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL
python -m src.cli eval --llm openai
```

结果写到 `examples/runs/<模型名>/`（每次运行一份 `.md` 和 `.json` Trace）和 `examples/results/<模型名>-summary.md`。

| 想看什么 | 文件 |
|---|---|
| 验收汇总（Mock） | [examples/results/mock-summary.md](examples/results/mock-summary.md) |
| 参考实例：18:00 冲突 → 建议 19:00 待确认 | [examples/runs/mock/c04_slot_conflict.md](examples/runs/mock/c04_slot_conflict.md) |
| 换占用时段后建议随之改变 | [examples/runs/mock/c09_conflict_shifted.md](examples/runs/mock/c09_conflict_shifted.md) |
| 重复提交只产生一份草稿 | [examples/runs/mock/c06_duplicate_submit_run2.md](examples/runs/mock/c06_duplicate_submit_run2.md) |
| 保存失败如实返回 | [examples/runs/mock/c07_save_failure.md](examples/runs/mock/c07_save_failure.md) |
| 真实模型三轮结果（GLM-4-Flash） | [第 1 轮](examples/results/glm-4-flash-r1-summary.md) / [第 2 轮](examples/results/glm-4-flash-r2-summary.md) / [第 3 轮](examples/results/glm-4-flash-r3-summary.md)，分析见 [docs/03-evaluation.md](docs/03-evaluation.md) |
| 测试输出 | [examples/results/pytest.txt](examples/results/pytest.txt) |

## 环境

- Python 3.10+（开发环境 3.13.4，Windows 11）
- 依赖：`openai`（仅真实模型需要）、`pytest`
- 环境变量见 [.env.example](.env.example)；Mock 模式无需配置

## 验收点与用例

| 验收点 | 用例（`examples/cases/`） |
|---|---|
| 正常排期 | `c01_normal` |
| 素材信息缺失 | `c02_missing_info`（缺封面/版权 + 不存在的 ID） |
| 规则风险 | `c03_rule_risk`（极限词阻断；未核验配乐补查后一项通过、一项阻断） |
| 时段冲突 | `c04_slot_conflict`（参考实例）、`c05_fixed_time_conflict`（硬性时间不得改）、`c09_conflict_shifted`（更换占用时段） |
| 重复提交 | `c06_duplicate_submit`、`c08_user_confirms_alternative`（确认后同一草稿升版本） |
| 保存失败 | `c07_save_failure` |
| 步数上限 | `c10_step_limit` |

自己出题：复制任一用例改 `request` 或 `env`（如 `extra_booked` 增加占用、`asset_overrides` 改素材字段、`faults` 注入故障），然后 `python -m src.cli run 你的用例.json --llm openai`。

## 目录

```
src/core/      与业务无关的 ReAct 内核：模型接入、循环、工具注册/故障注入、Trace、用例运行
src/domain/    本题业务：工具、提示词、结束护栏、离线 Mock 策略、验收检查
src/cli.py     命令行入口
data/          合成素材、审核规则、音乐授权库、已有排期
examples/      cases/ 输入；runs/ 实际输出与 Trace；results/ 汇总与测试输出
tests/         内核测试、业务测试、全部用例的验收测试
docs/          需求、方案、评估、AI 使用说明、复盘
```

## 已知限制

- `examples/runs/mock/` 是离线 Mock 的记录，只证明流程、工具、护栏打通；真实模型的决策效果以 `--llm openai` 的运行记录为准。
- 时段为整点、同日内找替代；没有跨日排期、渠道频控、多人并发编辑草稿。
- 草稿存为本地 JSON 文件，没有真实发布接口（按题意）。
