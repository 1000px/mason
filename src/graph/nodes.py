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
    image_keywords = ["生成图片", "画一张", "画一幅", "文生图", "图生图", "生成图像", "创作一幅",
                      "画个", "画一个", "生成一张", "generate image", "create image",
                      "修改图片", "重绘", "改图", "p图", "修图", "风格迁移"]
    
    if any(keyword in last_msg for keyword in image_keywords):
        return {"current_agent": "gen_image"}
    elif any(keyword in last_msg for keyword in code_keywords):
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

    system_content = agent.base_prompt
    if long_term_memory:
        system_content += f"\n\n## 🧠 Long-term Memory:\n{long_term_memory}"
    
    # 3. 准备工具列表
    # General 用 Skills, Coder 用 Tools (或者你也可以混合)
    if agent_name == "coder":
        tools_to_bind = TOOLS_SCHEMA
    else:
        tools_to_bind = skill_loader.get_all_schemas()
        
    if tools_to_bind:
        tool_descriptions = []
        for t in tools_to_bind:
            name = t["function"]["name"]
            desc = t["function"]["description"]
            tool_descriptions.append(f"- **{name}**: {desc}")
        system_content += "\n\n## 🛠️ Available Tools:\n" + "\n".join(tool_descriptions)
    

    messages = [SystemMessage(content=system_content)] + state["messages"]
    
    # 4. 绑定工具并执行
    # 关键点：确保 LLM 知道有哪些工具可用
    if tools_to_bind:
        llm = get_llm().bind_tools(tools_to_bind)
    else:
        llm = get_llm()
    res = llm.invoke(messages)
    
    return {"messages": [res]}

# ---- ✅ 工具执行节点 ----
def tool_node(state):
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {}
    
    msgs = []
    for tc in last.tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]
        
        # 判断是 Skill 还是 Tool
        skill = skill_loader.get_skill(tool_name)
        
        try:
            if skill:
                # 执行 Skill
                out = skill.execute(**tool_args)
            elif tool_name in TOOLS_REGISTRY:
                # 执行普通 Tool
                out = TOOLS_REGISTRY[tool_name](**tool_args)
            else:
                out = f"Unknown tool or skill: {tool_name}"
        except Exception as e:
            out = f"Execution Error: {str(e)}"
        
        msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))

    return {"messages": msgs}
