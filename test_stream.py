import uuid
from langchain_core.messages import HumanMessage, AIMessage
from src.graph.builder import build_graph
from src.db.memory import get_memory_store

def test_stream():
    graph = build_graph()
    store = get_memory_store()
    thread_id = str(uuid.uuid4())
    
    print("Testing stream:")
    for msg, metadata in graph.stream(
        {"messages": [HumanMessage(content="请写一段关于Python的简介，至少100字")], "current_agent": "router"},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="messages"
    ):
        print(f"msg type: {type(msg)}, content: '{msg.content}', metadata: {metadata}")

if __name__ == "__main__":
    test_stream()
