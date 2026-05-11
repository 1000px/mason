import json
import re
from langchain_core.messages import (
    AIMessage,
    ToolMessage,
    SystemMessage,
    HumanMessage,
)
from src.agents import AGENT_REGISTRY
from src.tools import TOOLS_REGISTRY, TOOLS_SCHEMA
from src.llm.provider import get_llm

# ---- Router ----
def router_node(state, store):
    llm = get_llm()
    messages = state["messages"]
    
    if not messages:
        return {"current_agent": "general"}
    
    res = llm.invoke([
        SystemMessage(content="You are a router. Respond ONLY with JSON: {\"agent\": \"coder\"} or {\"agent\": \"general\"}"),
        messages[-1]
    ])
    try:
        agent = json.loads(res.content)["agent"]
    except:
        agent = "general"
    return {"current_agent": agent}

# ---- 长期记忆提取（无调试输出）----
def memory_extraction_node(state, store):
    messages = state["messages"]
    if not messages:
        return {}
    
    last_msg = messages[-1]
    if last_msg.type != "human":
        return {}
    
    user_msg = last_msg.content
    namespace = ("user_profile",)
    
    # 检查是否已有记忆
    existing_memories = store.search(namespace)
    
    # 如果已有记忆，且用户输入不包含更新记忆的关键词，跳过
    if existing_memories:
        update_keywords = ["我叫", "我是", "我的", "我喜欢", "我讨厌", "我的爱好"]
        if not any(keyword in user_msg for keyword in update_keywords):
            return {}
    
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
    
    消息：{user_msg}"""
    
    try:
        res = llm.invoke([HumanMessage(content=prompt)])
        
        # 尝试多种 JSON 解析方式
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
    
    return {}

# ---- Agent Executor（无调试输出）----
def agent_executor_node(state, store):
    agent_name = state["current_agent"]
    agent = AGENT_REGISTRY[agent_name]
    
    # 从 store 加载长期记忆
    try:
        namespace = ("user_profile",)
        memories = store.search(namespace)
        
        if memories:
            long_term_memory_list = []
            for m in memories:
                memory_value = m.value
                if memory_value and memory_value.lower() != "none":
                    long_term_memory_list.append(f"{m.key}: {memory_value}")
            
            long_term_memory = "\n".join(long_term_memory_list)
        else:
            long_term_memory = ""
    except:
        long_term_memory = ""
    
    # 构建 System Prompt
    system_content = agent.base_prompt
    if long_term_memory:
        system_content += f"\n\n## 🧠 Long-term Memory (NEVER FORGET):\n{long_term_memory}"
    
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