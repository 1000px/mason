from langchain_core.messages import (
    AIMessage,
    ToolMessage,
    SystemMessage,
    HumanMessage,
)
from src.agents import AGENT_REGISTRY
from src.tools import TOOLS_REGISTRY, TOOLS_SCHEMA
from src.llm.provider import get_llm

# ---- 路由器（规则路由）----
def router_node(state, store):
    messages = state["messages"]
    if not messages:
        return {"current_agent": "general"}
    
    last_msg = messages[-1].content.lower()
    code_keywords = ["代码", "编程", "写代码", "debug", "函数", "算法", "python"]
    
    if any(keyword in last_msg for keyword in code_keywords):
        return {"current_agent": "coder"}
    else:
        return {"current_agent": "general"}

# ---- Agent Executor（只负责回答）----
def agent_executor_node(state, store):
    agent_name = state["current_agent"]
    agent = AGENT_REGISTRY[agent_name]
    
    # 加载长期记忆
    try:
        namespace = ("user_profile",)
        memories = store.search(namespace)
        long_term_memory = ""
        if memories:
            long_term_memory = "\n".join([f"{m.key}: {m.value}" for m in memories])
    except:
        long_term_memory = ""
    
    system_content = agent.base_prompt
    if long_term_memory:
        system_content += f"\n\n## 🧠 Long-term Memory:\n{long_term_memory}"
    
    messages = [SystemMessage(content=system_content)] + state["messages"]
    
    if agent_name == "coder":
        llm = get_llm().bind_tools(TOOLS_SCHEMA)
        res = llm.invoke(messages)
    else:
        llm = get_llm()
        res = llm.invoke(messages)
    
    return {"messages": [res]}

# ---- Tool Runner ----
def tool_node(state):
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {}
    
    msgs = []
    for tc in last.tool_calls:
        fn = TOOLS_REGISTRY.get(tc["name"])
        out = fn(**tc["args"]) if fn else "Tool not found"
        msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
    
    return {"messages": msgs}