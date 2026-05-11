from langgraph.graph import StateGraph, END
from src.db.memory import get_checkpointer, get_memory_store
from src.graph.nodes import (
    router_node,
    agent_executor_node,
    tool_node,
)
from src.graph.state import MasonState

def after_agent(state):
    """检查 agent 执行后是否需要调用工具"""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END

def build_graph():
    checkpointer = get_checkpointer()
    store = get_memory_store()
    
    g = StateGraph(MasonState)
    
    # ✅ 添加节点
    g.add_node("router", router_node)
    g.add_node("general", agent_executor_node)
    g.add_node("coder", agent_executor_node)
    g.add_node("tools", tool_node)
    
    # ✅ 设置入口
    g.set_entry_point("router")
    
    # ✅ 路由器决定下一个节点
    g.add_conditional_edges(
        "router",
        lambda s: s["current_agent"],
        {"general": "general", "coder": "coder"}
    )
    
    # ✅ 通用 Agent 后的条件边
    g.add_conditional_edges(
        "general",
        after_agent,
        {"tools": "tools", END: END}
    )
    
    # ✅ Coder Agent 后的条件边
    g.add_conditional_edges(
        "coder",
        after_agent,
        {"tools": "tools", END: END}
    )
    
    # ✅ 工具执行完后回到 coder
    g.add_edge("tools", "coder")
    
    return g.compile(checkpointer=checkpointer, store=store)