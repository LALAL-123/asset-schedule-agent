# 提交说明（可直接粘贴到提交框）

- 题号：1（素材审核与发布排期 Agent）
- GitHub URL：（推送后填写）
- 最终 commit SHA：（推送后填写）
- 实际用时：（本人填写）

---

原生 Python 实现 ReAct 循环：模型通过 function calling 选择工具（读取素材、规则检查、授权补查、时段查询、保存草稿），观察结果后决定下一步，调用 finish 提交结构化结果。设有步数与工具调用上限，超限返回 incomplete。模型接 OpenAI 兼容接口（DeepSeek/通义/OpenAI），另有离线 Mock 入口仅用于验证流程。

动态决策：配乐未核验 → 补查授权后通过或阻断；要求时段被占 → flexible 时选附近空闲时段并标记待确认，fixed 时不改时间、请求确认；保存失败 → 重试或如实报告 save_failed。

确认边界与防重复：save_draft 服务端复核审核结论、时段占用和硬性时间；finish 后护栏用工具记录核对结论（不虚报保存、不称已发布、改过的时段必须待确认）；草稿按 request_id 幂等，相同内容去重，内容变化升版本。

验证：10 个用例覆盖正常排期、信息缺失、规则风险、时段冲突（含参考实例与更换占用时段）、重复提交、保存失败、步数上限；pytest 全部通过，Mock 评估 50/50。Trace 在 examples/runs/，汇总在 examples/results/，评估说明在 docs/03-evaluation.md。

真实模型（智谱 GLM-4-Flash）三轮：31/50 → 29/50 → 36/50。每轮读 Trace 定位问题后修改（未审完就结束改为退回模型、错误里列出空闲时段、修正授权库数据缺陷）；三轮中护栏挡下了全部虚报保存与“已发布”表述。未通过项与归因见 docs/03-evaluation.md。

评审入口：`pip install -r requirements.txt && python -m pytest -q && python -m src.cli eval --llm mock`；真实模型见 README。

已知限制：Mock 记录只证明流程；同日内找替代时段，不跨日；草稿存本地 JSON。
