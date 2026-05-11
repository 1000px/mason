import logging
import httpx

# 关闭所有第三方库的 INFO / DEBUG 日志
logging.basicConfig(level=logging.WARNING)

# 单独关掉 httpx 的日志（最关键）
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("langgraph").setLevel(logging.WARNING)

import uuid
import json
import re
from langchain_core.messages import HumanMessage, AIMessage
from src.graph.builder import build_graph
from src.db.memory import get_memory_store
from src.llm.provider import get_llm

def extract_memory_from_input(user_input, store):
    """从用户输入中提取记忆（独立函数，不在图中）"""
    namespace = ("user_profile",)
    
    # 检查是否需要更新记忆
    update_keywords = ["我叫", "我是", "我的", "我喜欢", "我讨厌"]
    if not any(keyword in user_input for keyword in update_keywords):
        return
    
    llm = get_llm()
    prompt = f"""从用户消息中提取所有个人信息，返回JSON格式。
    必须提取以下信息（如果存在）：
    - name: 姓名
    - job: 职业
    - hobby: 爱好
    - like: 喜欢的事物
    - dislike: 不喜欢的事物
    - location: 所在地
    - age: 年龄
    
    示例：
    输入："我叫Lucio，是个程序员，我喜欢蓝色，我爱打篮球"
    输出：{{"name": "Lucio", "job": "programmer", "like": "blue", "hobby": "basketball"}}
    
    消息：{user_input}"""
    
    try:
        res = llm.invoke([HumanMessage(content=prompt)])
        facts = None
        try:
            facts = json.loads(res.content)
        except:
            json_match = re.search(r'\{.*\}', res.content, re.DOTALL)
            if json_match:
                facts = json.loads(json_match.group())
        
        if facts:
            for key, value in facts.items():
                if value and str(value).lower() != "none":
                    store.put(namespace, key, str(value))
    except:
        pass

def main():
    print("🦖 Mason Stage 6 (Pure Streaming + Memory)\n")
    
    graph = build_graph()
    store = get_memory_store()  # ✅ 获取 store 实例
    thread_id = str(uuid.uuid4())
    
    while True:
        q = input("You: ")
        if q.lower() == "exit":
            break
        
        # ✅ 第一步：独立提取记忆（不在图中）
        extract_memory_from_input(q, store)
        
        print("Mason: ", end="", flush=True)
        
        # ✅ 第二步：只执行图（没有记忆提取节点）
        for msg, metadata in graph.stream(
            {"messages": [HumanMessage(content=q)], "current_agent": "router"},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="messages"
        ):
            if isinstance(msg, AIMessage) and msg.content:
                print(msg.content, end="", flush=True)
        
        print()

if __name__ == "__main__":
    main()