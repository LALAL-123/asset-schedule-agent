"""ReAct 内核测试：用逐条回放的假模型验证循环、上限、错误处理。不依赖业务数据。"""
from src.core.agent import ReActAgent
from src.core.llm import LLMReply, ToolCall
from src.core.tools import FaultPlan, Tool, ToolError, ToolRegistry

FINISH_PARAMS = {"type": "object", "properties": {"task_status": {"type": "string"}}, "required": ["task_status"]}


def call(name, **args):
    args.setdefault("decision_note", f"测试：调用 {name}")
    return ToolCall(f"id_{name}_{len(args)}", name, args)


class SeqLLM:
    name = "test:seq"

    def __init__(self, replies, default=None):
        self.replies = list(replies)
        self.default = default

    def chat(self, messages, tools):
        if self.replies:
            r = self.replies.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        return self.default


seen_args = []


def echo(text):
    seen_args.append(text)
    return {"echo": text}


def boom():
    raise ToolError("存储不可用")


TOOLS = [
    Tool("echo", "回显", {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}, echo),
    Tool("boom", "总是失败", {"type": "object", "properties": {}}, boom),
]


def make(llm, max_steps=4, max_calls=10, faults=None, guard=None):
    return ReActAgent(
        llm=llm,
        registry=ToolRegistry(TOOLS, FaultPlan(faults)),
        system_prompt="test",
        finish_parameters=FINISH_PARAMS,
        guard=guard or (lambda a, r, p: (dict(a), [])),
        on_incomplete=lambda records, payload, reason: {"completed_calls": [r.tool for r in records if r.ok]},
        max_steps=max_steps,
        max_tool_calls=max_calls,
    )


def test_step_limit_returns_explicit_incomplete():
    loop = LLMReply("", [call("echo", text="again")])
    res = make(SeqLLM([], default=loop), max_steps=3).run({})
    assert res.status == "incomplete" and res.stop_reason == "step_limit_reached"
    assert res.steps == 3 and res.final["completed_calls"] == ["echo"] * 3
    assert res.trace[-1]["type"] == "stop"


def test_tool_call_limit_stops_run():
    loop = LLMReply("", [call("echo", text="a"), call("echo", text="b")])
    res = make(SeqLLM([], default=loop), max_steps=10, max_calls=3).run({})
    assert res.status == "incomplete" and res.stop_reason == "tool_call_limit_reached"
    assert res.tool_calls == 3


def test_finish_in_same_turn_as_tool_is_rejected():
    llm = SeqLLM([
        LLMReply("", [call("echo", text="x"), call("finish", task_status="completed")]),
        LLMReply("", [call("finish", task_status="completed")]),
    ])
    res = make(llm).run({})
    assert res.status == "completed" and res.steps == 2
    rejected = [t for t in res.trace if t.get("tool") == "finish"]
    assert rejected and "finish_rejected" in rejected[0]["observation"]


def test_decision_note_is_traced_but_not_passed_to_tool():
    seen_args.clear()
    llm = SeqLLM([LLMReply("", [call("echo", text="hi", decision_note="依据输入")]),
                  LLMReply("", [call("finish", task_status="completed")])])
    res = make(llm).run({})
    assert seen_args == ["hi"]
    assert res.trace[0]["decision_note"] == "依据输入"


def test_tool_errors_become_observations():
    llm = SeqLLM([
        LLMReply("", [call("nope"), call("echo"), call("boom")]),
        LLMReply("", [call("finish", task_status="failed")]),
    ])
    res = make(llm).run({})
    obs = [t["observation"] for t in res.trace if t["type"] == "tool_call"]
    assert "unknown_tool" in obs[0] and "invalid_arguments" in obs[1] and "存储不可用" in obs[2]
    assert res.status == "failed"


def test_fault_plan_once_then_recovers():
    llm = SeqLLM([LLMReply("", [call("echo", text="1")]), LLMReply("", [call("echo", text="2")]),
                  LLMReply("", [call("finish", task_status="completed")])])
    res = make(llm, faults={"echo": {"mode": "once"}}).run({})
    oks = [t["ok"] for t in res.trace if t["type"] == "tool_call"]
    assert oks == [False, True]


def test_llm_exception_returns_failed():
    res = make(SeqLLM([RuntimeError("timeout")])).run({})
    assert res.status == "failed" and res.stop_reason == "llm_error"


def test_invalid_finish_is_sent_back_to_model():
    state = {"n": 0}

    def strict_guard(args, records, payload):
        state["n"] += 1
        if state["n"] == 1:
            raise ValueError("缺少 items")
        return dict(args), []

    llm = SeqLLM([LLMReply("", [call("finish", task_status="completed")]),
                  LLMReply("", [call("finish", task_status="completed")])])
    res = make(llm, guard=strict_guard).run({})
    assert res.status == "completed" and res.steps == 2
    assert "invalid_finish" in res.trace[0]["observation"]


def test_text_reply_without_tool_is_nudged():
    llm = SeqLLM([LLMReply("我觉得完成了", []), LLMReply("", [call("finish", task_status="completed")])])
    res = make(llm).run({})
    assert res.trace[0]["type"] == "no_tool_call" and res.status == "completed"


def test_openai_compat_parses_tool_calls_and_bad_json():
    """不联网：用假的 client 验证真实模型接入层对 tool_calls 的解析。"""
    from types import SimpleNamespace as NS

    from src.core.llm import OpenAICompatLLM

    calls = [NS(id="c1", function=NS(name="echo", arguments='{"text": "hi", "decision_note": "n"}')),
             NS(id="c2", function=NS(name="echo", arguments='{bad json'))]
    sent = {}

    def create(**kw):
        sent.update(kw)
        return NS(choices=[NS(message=NS(content=None, tool_calls=calls))])

    llm = OpenAICompatLLM.__new__(OpenAICompatLLM)
    llm.client = NS(chat=NS(completions=NS(create=create)))
    llm.model, llm.temperature, llm.tool_choice, llm.name = "m", 0.0, "auto", "openai-compat:m"
    reply = llm.chat([{"role": "user", "content": "x"}], [TOOLS[0].schema()])
    assert reply.tool_calls[0].arguments == {"text": "hi", "decision_note": "n"}
    assert reply.tool_calls[1].parse_error and reply.tool_calls[1].arguments == {}
    assert sent["tools"][0]["function"]["parameters"]["required"] == ["text", "decision_note"]


def test_text_tool_call_is_recovered_only_with_name_and_json():
    from src.core.llm import recover_text_tool_calls

    text = '当前步骤：完成\n调用工具：finish\n参数：{"task_status": "completed", "decision_note": "检查通过"}'
    calls = recover_text_tool_calls(text, ["echo", "finish"], 3)
    assert calls[0].name == "finish" and calls[0].arguments["task_status"] == "completed"
    assert recover_text_tool_calls("我已经完成了，结果是 finish。", ["finish"]) == []
    assert recover_text_tool_calls('unknown_tool {"a": 1}', ["finish"]) == []


def test_agent_executes_recovered_text_call_and_marks_trace():
    llm = SeqLLM([LLMReply('调用工具：echo\n参数：{"text": "hi", "decision_note": "n"}', []),
                  LLMReply("", [call("finish", task_status="completed")])])
    res = make(llm).run({})
    assert res.status == "completed" and res.trace[0]["recovered_from_text"] is True
    assert res.records[0].result["echo"] == "hi"
