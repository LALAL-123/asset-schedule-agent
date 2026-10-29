# 02 方案

## 调用流程

```
用户请求 ──► ReActAgent.run
              │  messages = [system, 任务输入]
              ▼
        ┌──► 模型（OpenAI 兼容 / 离线 Mock）选择动作 + decision_note
        │     │
        │     ├─ 业务工具 ──► ToolRegistry（参数检查、故障注入、异常转观察）
        │     │                 └─ 结果作为 tool 消息回到对话
        │     │
        │     └─ finish ──► guard：用工具事实校验结论 ──► 最终结果
        │
        └── 未 finish 且未超限：进入下一轮
              超过 max_steps / max_tool_calls ──► incomplete + 已完成部分
```

工具（`src/domain/tools.py`）：

| 工具 | 作用 | 关键返回 |
|---|---|---|
| `read_asset` | 读取素材元数据 | `found`、`asset` |
| `check_rules` | 按 R01–R04 检查 | `result`、`issues` |
| `lookup_license` | 补查配乐授权 | `status`: valid / expired / not_found |
| `query_slots` | 查时段是否空闲 | `available`、`occupied_by`、`free_slots_nearby` |
| `save_draft` | 保存排期草稿 | `draft_id`、`version`、`deduplicated`；失败时 `ok=false` |

## 动态决策点

循环代码里没有业务分支，下一步由模型看观察结果决定。系统提示词给出业务规则，工具返回事实：

| 观察 | 可选动作 |
|---|---|
| `check_rules.result = needs_verification` | 调 `lookup_license` 补查；valid → 继续排期，expired/not_found → 阻断 |
| `missing_info` / `risk` / `found=false` | 不查时段，直接写原因和待确认项 |
| `query_slots.available = false`，flexible | 从 `free_slots_nearby` 选替代时段，标记待确认 |
| `query_slots.available = false`，fixed | 不改时间，`conflict_fixed`，请求用户确认是否放宽 |
| `user_confirmations` 有该素材 | 查询该时段仍空闲后按已确认排期 |
| `save_draft` 工具失败 | 重试一次或直接报告 `save_failed` |
| `save_draft` 校验失败（`validation_failed`） | 按错误调整草稿内容或放弃该项 |

两条对照路径（同一素材，只改工具结果）：

- `c04`：18:00 被占 → 建议 19:00；`c09`：19:00 也被占 → 建议 16:00。
- `c03`：M05 补查授权 valid → 排期；M06 补查 expired → 阻断。

## 三层保证

1. **提示词**约定业务规则（硬性时间不可改、只存草稿）。
2. **工具服务端校验**：`save_draft` 自己复核审核结论（含授权库）、时段占用、硬性时间，不信任调用方传来的状态。
3. **结束护栏** `guard`：模型调用 `finish` 后，用已执行的工具记录逐项核对——审核未通过不能排期、建议时段必须被 `query_slots` 确认空闲、改时段必须待确认、`draft.saved` 以 `save_draft` 返回为准、`task_status` 按事实重算、清除“已发布”表述。所有校正写入 `guard_corrections`，在 Trace 中可见。

护栏不替模型选动作，只拦截与事实不符的结论。如果真实模型频繁触发校正，说明提示词或工具设计需要改进，这本身是评估信号。

## 防重复

草稿按 `request_id` 建键（无 `request_id` 时用请求内容哈希），幂等键由系统注入而不是让模型传：

- 内容相同 → 返回已有草稿，`deduplicated=true`，不新建；
- 内容变化（例如用户确认了替代时段）→ 同一草稿 `version+1`。

## 技术取舍

| 选择 | 理由 | 代价 |
|---|---|---|
| 原生实现循环，不用 LangGraph/ADK | 循环约 150 行，步数上限、finish 校验、Trace 字段都能精确控制，便于解释 | 没有现成的持久化/可视化 |
| OpenAI 兼容接口 | 一份代码可切 DeepSeek/通义/OpenAI | 各家 function calling 细节有差异（如 `tool_choice=required` 支持不一），用 `LLM_TOOL_CHOICE` 配置 |
| 每个工具自动加必填参数 `decision_note` | 决策依据和动作一起产生，不需要模型输出思维过程 | 多占少量 token；执行前剥离 |
| 用 `finish` 工具提交结构化结果 | 结果可校验，不用解析自由文本 | 模型可能过早 finish；同轮混调 finish 会被拒绝 |
| `finish` 不能与业务工具同轮调用 | 防止模型没看到结果就下结论 | 多一轮 |
| 离线 Mock = 确定性策略 | 无密钥时也能跑通全部用例与测试 | 只验证流程，不代表模型能力 |
| 故障注入放在 `ToolRegistry` | 任意工具、任意次数失败都能复现 | 只模拟返回失败，不模拟超时 |
