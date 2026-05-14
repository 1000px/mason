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

def after_tools(state):
    """工具执行完后，回到触发工具的那个 Agent"""
    # 回到当前的 agent (general 或 coder)
    return state["current_agent"]

def build_graph():
    checkpointer = get_checkpointer()
    store = get_memory_store()
    
    g = StateGraph(MasonState)
    
    # ✅ 添加节点
    g.add_node("router", router_node)
    g.add_node("general", agent_executor_node)
    g.add_node("coder", agent_executor_node)
    g.add_node("gen_image", agent_executor_node)
    g.add_node("tools", tool_node)
    
    # ✅ 设置入口
    g.set_entry_point("router")
    
    # ✅ 路由器决定下一个节点
    g.add_conditional_edges(
        "router",
        lambda s: s["current_agent"],
        {"general": "general", "coder": "coder", "gen_image": "gen_image"}
    )
    
   # Agent 后判断
    g.add_conditional_edges("general", after_agent, {"tools": "tools", END: END})
    g.add_conditional_edges("coder", after_agent, {"tools": "tools", END: END})
    g.add_conditional_edges("gen_image", after_agent, {"tools": "tools", END: END})
    
    # ✅ 修复：工具执行完后，回到原来的 Agent
    g.add_conditional_edges("tools", after_tools, {"general": "general", "coder": "coder", "gen_image": "gen_image"})
    
    return g.compile(checkpointer=checkpointer, store=store)