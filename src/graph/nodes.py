from langchain_core.messages import (
    AIMessage,
    ToolMessage,
    SystemMessage,
    HumanMessage,
)
from src.agents import AGENT_REGISTRY
from src.tools import TOOLS_REGISTRY, TOOLS_SCHEMA, ALL_TOOLS
from src.llm.provider import get_llm
from src.skills.loader import skill_loader

# ---- 路由器（规则路由）----
def router_node(state, store):
    messages = state["messages"]
    if not messages:
        return {"current_agent": "general"}
    
    last_msg = messages[-1].content.lower()
    code_keywords = ["代码", "编程", "写代码", "debug", "函数", "算法", "python", "shell", "命令"]
    
    if any(keyword in last_msg for keyword in code_keywords):
        return {"current_agent": "coder"}
    else:
        return {"current_agent": "general"}

# ---- Agent Executor ----
def agent_executor_node(state, store):
    agent_name = state["current_agent"]
    agent = AGENT_REGISTRY[agent_name]
    
    # 加载长期记忆
    try:
        namespace = ("user_profile",)
        memories = store.search(namespace)
        long_term_memory = "\n".join([f"{m.key}: {m.value}" for m in memories]) if memories else ""
    except:
        long_term_memory = ""
    
    # 加载Skill清单
    skill_list = "\n".join([
        f"- {name}: {skill.description.strip()}"
        for name, skill in skill_loader.skills.items()
    ])
    # skill_tools = skill_loader.get_all_tools()

    system_content = agent.base_prompt
    if long_term_memory:
        system_content += f"\n\n## 🧠 Long-term Memory:\n{long_term_memory}"
    # if skill_tools:
    #     skill_list = "\n".join([f"- {t.name}: {t.description}" for t in skill_tools])
    #     system_content += f"\n\n## 🛠️ Available Skills:\n{skill_list}"
    if skill_list:
        system_content += f"\n\n## 🛠️ Available Skills:\n{skill_list}"
        system_content += "\n\nWhen a user asks you to do something related to these skills, call the function directly."

    messages = [SystemMessage(content=system_content)] + state["messages"]

    # 4. 🆕 绑定 Skills (替代原来的 bind_tools)
    # 注意：我们需要把 skill 的 execute 方法作为工具函数传给 LLM
    # skill_functions = [skill.execute for skill in skill_loader.skills.values()]
    # if skill_tools:
    #     llm = agent.llm.bind_tools(skill_tools)
    # else:
    #     llm = agent.llm

    # 4. 绑定 Skills (使用纯 Schema 列表)
    skill_schemas = skill_loader.get_all_schemas()
    
    if skill_schemas:
        llm = get_llm().bind_tools(skill_schemas)
    else:
        llm = get_llm()
    # llm = get_llm().bind_tools(skill_functions)
    res = llm.invoke(messages)
    
    return {"messages": [res]}

# ---- ✅ 工具执行节点 ----
def tool_node(state):
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {}
    
    msgs = []
    for tc in last.tool_calls:
        skill = skill_loader.get_skill(tc["name"])
        if skill:
            try:
                out = skill.execute(**tc["args"])
            except Exception as e:
                out = f"Skill Execution Error: {str(e)}"
        else:
            out = f"Unknown skill: {tc['name']}"
        
        msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
    
    return {"messages": msgs}
# def tool_node(state):
#     last = state["messages"][-1]
#     if not isinstance(last, AIMessage) or not last.tool_calls:
#         return {}
    
#     msgs = []
#     for tc in last.tool_calls:
#         # 🆕 从 Skill Loader 中获取执行器
#         skill = skill_loader.get_skill(tc["name"])
#         if skill:
#             try:
#                 out = skill.execute(**tc["args"])
#             except Exception as e:
#                 out = f"Skill Execution Error: {str(e)}"
#         else:
#             out = f"Unknown skill: {tc['name']}"
        
#         msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
    
#     return {"messages": msgs}