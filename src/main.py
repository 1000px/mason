import logging
import httpx

# 关闭所有第三方库的 INFO / DEBUG 日志
logging.basicConfig(level=logging.WARNING)

# 单独关掉 httpx 的日志（最关键）
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("langgraph").setLevel(logging.WARNING)

import uuid
from langchain_core.messages import HumanMessage
from src.graph.builder import build_graph

def main():
    print("🦖 Mason Stage 6 (Ready for Web UI)\n")
    
    graph = build_graph()
    thread_id = str(uuid.uuid4())
    
    while True:
        q = input("You: ")
        if q.lower() == "exit":
            break
        
        print("Mason: ", end="", flush=True)
        
        # ✅ 使用流式输出
        for chunk in graph.stream(
            {"messages": [HumanMessage(content=q)], "current_agent": "router"},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates"
        ):
            if not chunk:
                continue
            
            for node_name, update in chunk.items():
                if not update or "messages" not in update:
                    continue
                
                msg = update["messages"][-1]
                if hasattr(msg, "content") and msg.content:
                    print(msg.content, end="", flush=True)
        
        print()

if __name__ == "__main__":
    main()