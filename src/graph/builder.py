from src.graph.state import MasonState

from langgraph.graph import StateGraph, END
from src.db.memory import get_checkpointer, get_memory_store
from src.graph.nodes import (
    router_node,
    memory_extraction_node,
    agent_executor_node,
    tool_node,
)

def after_agent(state):
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END

def build_graph():
    checkpointer = get_checkpointer()
    store = get_memory_store()
    
    g = StateGraph(MasonState)
    
    g.add_node("router", router_node)
    g.add_node("extract_memory", memory_extraction_node)
    g.add_node("general", agent_executor_node)
    g.add_node("coder", agent_executor_node)
    g.add_node("tools", tool_node)
    
    g.set_entry_point("router")
    g.add_edge("router", "extract_memory")
    
    g.add_conditional_edges(
        "extract_memory",
        lambda s: s["current_agent"],
        {"general": "general", "coder": "coder"}
    )
    
    g.add_conditional_edges(
        "general", after_agent, {"tools": "tools", END: END}
    )
    g.add_conditional_edges(
        "coder", after_agent, {"tools": "tools", END: END}
    )
    
    g.add_edge("tools", "coder")
    
    return g.compile(checkpointer=checkpointer, store=store)