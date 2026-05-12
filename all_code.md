```
我使用python+langchain+langgraph开发了一个类似于openclaw的ai智能体，python版本，现在我遇到了一些困难，想进一步学习openclaw类似的skill操作，比如常用的skill的安装与使用，自定义skill，手动导入skill等，我希望你引导我进行余下的开发。
但在此之前，你需要了解我的项目架构和代码，我会分别将项目结构和每个文件的代码发给你，你认真研究、学习，理解，之后，引导我进行接下来的开发。
注意：我的目的是用python复写一个openclaw的python版本。现在，你准备好接受我提供的项目架构了吗？
```

# 这是整个项目的代码，每个二级标题对应一个文件，文件名包含文件路径

## README.md
```
# mason
mason agent ai，石匠铺子，python版本OpenClaw

# 开发周期

阶段一：MVP (最小可行性产品) —— “会说话的终端”

目标：打通 LangGraph 的基础循环，让 Agent 能在终端里接收输入并回复。

核心逻辑：实现一个最简单的 ReAct（Reason+Act）循环。

不包含：工具执行、沙箱、多模型切换、记忆持久化。

交付物：一个能通过 python main.py启动的 CLI 聊天机器人。

阶段二：工具集成 —— “赋予手脚”

目标：复刻 OpenClaw 的核心能力——调用 Shell 和 Python 代码。

核心逻辑：定义 Tool Schema，实现 LangChain Tools，并在 Graph 中加入 Tool Execution Node。

关键点：模拟 OpenClaw 的 !shell和 !python指令解析。

阶段三：沙箱与安全 —— “戴上镣铐”

目标：复刻 OpenClaw 的安全机制。

核心逻辑：引入 Docker 或 subprocess 隔离，实现 Permission Denied（权限拒绝）​ 和 Timeout（超时）​ 控制。

关键点：确保 Agent 不能随意删除系统文件。

阶段四：多智能体路由 —— “分派任务”

目标：复刻 OpenClaw 的 Router（路由器）。

核心逻辑：使用 LangGraph 的 Conditional Edges（条件边）。根据用户意图，将任务分发给不同的 Sub-Agent（如：Coding Agent vs Planning Agent）。

阶段五：记忆与上下文 —— “拥有大脑”

目标：实现长短期记忆。

核心逻辑：使用 LangChain 的 ConversationBufferMemory或 SummaryMemory，处理 Token 窗口限制。

阶段六：UI 与 API —— “穿上衣服”

目标：提供 Web UI 或 API 接口。

核心逻辑：封装 FastAPI，对接前端界面。
```

## requirements.txt

```
# Core LangChain & LangGraph (Latest Stable as of 2026-05)
langchain==1.2.0
langchain-core==1.3.0
langchain-openai==1.2.0
langgraph==1.0.10

langgraph-checkpoint-mysql>=2.0.0
pymysql==1.1.0
aiomysql==0.2.0
asyncmy>=0.2.0
# Environment & Utils
python-dotenv==1.1.0
pydantic==2.11.0

# Async runtime (Recommended for LangGraph streaming)
anyio==4.9.0

docker==7.1.0

# Web UI 依赖
fastapi>=0.115.2,<1.0
starlette>=0.40.0,<2.0
uvicorn==0.27.0
websockets==12.0
jinja2==3.1.3
```

## src/main.py

```python
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

```

## src/agents/__init__.py

```python
from .general import GeneralAgent
from .coder import CoderAgent

AGENT_REGISTRY = {
    "general": GeneralAgent(),
    "coder": CoderAgent()
}
```

## src/agents/base.py

```python
from langchain_core.prompts import ChatPromptTemplate
from src.llm.provider import get_llm

class BaseAgent:
    def __init__(self, system_prompt: str):
        self.base_prompt = system_prompt
        self.llm = get_llm()
```

## src/agents/general.py

```python
from .base import BaseAgent

GENERAL_PROMPT = """You are Mason, a helpful general assistant.
You are good at chatting, summarizing, and answering general questions.
If you don't know the answer, just say so.
Please return the result in natural language, without any special data structures such as JSON or the like.
"""

class GeneralAgent(BaseAgent):
    def __init__(self):
        super().__init__(GENERAL_PROMPT)
        self.name = "general"
        self.description = "General assistant for chatting, summarizing, and answering general questions."
```

## src/agents/coder.py

```python
from .base import BaseAgent

CODER_PROMPT = """You are Mason's Coding Agent.
You are an expert software engineer.
You have access to tools to execute shell commands and python code.
Use tools whenever you need to verify code, list files, or run tests.
"""

class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(CODER_PROMPT)
        self.name = "coder"
        self.description = "Expert software engineer for coding tasks."
```

## src/config/settings.py
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ACTIVE_PROVIDER: str = os.getenv("ACTIVE_MODEL_PROVIDER", "deepseek")
    
    # DeepSeek Config
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    
    # Qwen Config
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    # 🆕 Sandbox Config
    SANDBOX_TYPE: str = os.getenv("SANDBOX_TYPE", "local")  # "docker" or "local"
    SANDBOX_TIMEOUT: int = int(os.getenv("SANDBOX_TIMEOUT", "10"))  # seconds
    # MySQL Config
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "3306"))
    USER: str = os.getenv("USER", "root")
    PASSWORD: str = os.getenv("PASSWORD", "")
    DATABASE: str = os.getenv("DATABASE", "mason")
    CHARSET: str = os.getenv("CHARSET", "utf8mb4")

settings = Settings()
```

## src/db/memory.py
```python
import pymysql
from langgraph.store.mysql import PyMySQLStore
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
from src.config.settings import settings

# MySQL 连接配置
CONNECTION_CONFIG = {
    "host": settings.HOST,
    "port": settings.PORT,
    "user": settings.USER,
    "password": settings.PASSWORD,
    "database": settings.DATABASE,
    "charset": settings.CHARSET
}

def get_mysql_connection():
    """获取 MySQL 连接"""
    return pymysql.connect(**CONNECTION_CONFIG)

def get_checkpointer():
    """短期记忆（Checkpointer）"""
    conn = get_mysql_connection()
    checkpointer = PyMySQLSaver(conn)
    try:
        checkpointer.setup()
    except Exception:
        pass
    return checkpointer

def get_memory_store():
    """长期记忆（Store）"""
    conn = get_mysql_connection()
    store = PyMySQLStore(conn)
    try:
        store.setup()
    except Exception:
        pass
    return store

```

## src/graph/builder.py
```python
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
```

## src/graph/nodes.py

```python
from langchain_core.messages import (
    AIMessage,
    ToolMessage,
    SystemMessage,
    HumanMessage,
)
from src.agents import AGENT_REGISTRY
from src.tools import TOOLS_REGISTRY, TOOLS_SCHEMA, ALL_TOOLS
from src.llm.provider import get_llm

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
        long_term_memory = ""
        if memories:
            long_term_memory = "\n".join([f"{m.key}: {m.value}" for m in memories])
    except:
        long_term_memory = ""
    
    system_content = agent.base_prompt
    if long_term_memory:
        system_content += f"\n\n## 🧠 Long-term Memory:\n{long_term_memory}"
    
    messages = [SystemMessage(content=system_content)] + state["messages"]

    llm = get_llm().bind_tools(ALL_TOOLS)
    res = llm.invoke(messages)
    
    # if agent_name == "coder":
    #     # ✅ Coder 绑定工具
    #     llm = get_llm().bind_tools(ALL_TOOLS)
    #     res = llm.invoke(messages)
    # else:
    #     llm = get_llm()
    #     res = llm.invoke(messages)
    
    return {"messages": [res]}

# ---- ✅ 工具执行节点 ----
def tool_node(state):
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {}
    
    msgs = []
    for tc in last.tool_calls:
        fn = TOOLS_REGISTRY.get(tc["name"])
        if fn:
            try:
                out = fn(**tc["args"])
            except Exception as e:
                out = f"工具执行错误: {str(e)}"
        else:
            out = f"未知工具: {tc['name']}"
        
        msgs.append(ToolMessage(content=str(out), tool_call_id=tc["id"]))
    
    return {"messages": msgs}
```

## src/graph/state.py

```python
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages

class MasonState(TypedDict):
    """
    定义整个 Graph 流转的数据结构
    messages: 存储对话历史
    """
    messages: Annotated[list[AnyMessage], add_messages]
    # 记录当前活跃的Agent
    current_agent: Literal["router", "general", "coder"]
```

## src/llm/provider.py

```python
from langchain_openai import ChatOpenAI
from src.config.settings import settings

def get_llm(model_name: str | None = None):
    """
    根据配置动态返回 LLM 实例
    """
    provider = settings.ACTIVE_PROVIDER
    
    if provider == "deepseek":
        return ChatOpenAI(
            model=model_name or "deepseek-chat",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0.7,
        )
    elif provider == "qwen":
        return ChatOpenAI(
            model=model_name or "qwen-plus",
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            temperature=0.7,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
```

## src/sandbox/__init__.py
```python
import logging
from src.config.settings import settings
from .local_sandbox import LocalSandbox
from .docker_sandbox import DockerSandbox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sandbox():
    """
    获取沙箱实例。
    如果配置了 Docker 但初始化失败，自动降级为 Local 沙箱。
    """
    if settings.SANDBOX_TYPE == "docker":
        try:
            # 尝试初始化 Docker 沙箱
            sandbox = DockerSandbox()
            logger.info("✅ Docker Sandbox initialized successfully.")
            return sandbox
        except Exception as e:
            # 关键：捕获所有异常，降级为 Local
            logger.warning(f"⚠️ Docker Sandbox failed: {e}. Falling back to Local Sandbox.")
            return LocalSandbox()
    
    # 如果不是 docker，直接用 local
    return LocalSandbox()
```

## src/sandbox/base.py

```python
from abc import ABC, abstractmethod

class BaseSandbox(ABC):
    @abstractmethod
    def execute(self, command: str) -> str:
        """执行命令并返回结果"""
        pass

    @abstractmethod
    def execute_code(self, code: str, language: str = "python") -> str:
        """执行代码并返回结果"""
        pass
```

## src/sandbox/local_sandbox.py

```python
import subprocess
import tempfile
import os
from .base import BaseSandbox
from src.config.settings import settings

class LocalSandbox(BaseSandbox):
    def execute(self, command: str) -> str:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=10
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Execution Error: {e}"

    def execute_code(self, code: str, language: str = "python") -> str:
        if language != "python":
            return "Only python supported in local sandbox."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            fname = f.name
        
        try:
            result = subprocess.run(
                ["python", fname], capture_output=True, text=True, timeout=settings.SANDBOX_TIMEOUT
            )
            return result.stdout + result.stderr
        finally:
            os.unlink(fname)
```

## src/sandbox/docker_sandbox.py

```python
import docker
import tempfile
import os
from .base import BaseSandbox

class DockerSandbox(BaseSandbox):
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.image = "python:3.11-slim"
            
            # 检查镜像是否存在，不存在才拉取
            images = self.client.images.list(name=self.image)
            if not images:
                print(f"Pulling image {self.image}...")
                self.client.images.pull(self.image)
                
        except Exception as e:
            raise RuntimeError(f"Docker not available: {e}")
    def execute(self, command: str) -> str:
        """
        在 Docker 容器中执行 Shell 命令
        """
        try:
            container = self.client.containers.run(
                image=self.image,
                command=["sh", "-c", command],
                remove=True,  # 自动删除容器
                detach=False,
                stdout=True,
                stderr=True,
                network_disabled=True,  # 🔒 禁用网络
                mem_limit="128m",       # 🔒 内存限制
                cpu_period=100000,
                cpu_quota=50000,        # 🔒 限制 CPU 50%
            )
            return container.decode("utf-8", errors="ignore")
        except Exception as e:
            return f"Docker Execution Error: {e}"

    def execute_code(self, code: str, language: str = "python") -> str:
        """
        在 Docker 中执行 Python 代码
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            fname = f.name
        
        try:
            container = self.client.containers.run(
                image=self.image,
                command=["python", "/app/script.py"],
                volumes={fname: {'bind': '/app/script.py', 'mode': 'ro'}}, # 只读挂载
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                network_disabled=True,
                mem_limit="128m",
            )
            return container.decode("utf-8", errors="ignore")
        finally:
            os.unlink(fname)
```

## src/tools/__init__.py
```python
from .shell import execute_shell
from .python import execute_python

# 工具注册表（不用 Tool 类）
TOOLS_REGISTRY = {
    "execute_shell": execute_shell,
    "execute_python": execute_python
}

# 工具定义（给 LLM 看的 Schema）
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Execute a shell command. Use this to interact with the file system, run scripts, or manage processes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "Execute Python code. Use this for calculations, data processing, or complex logic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The Python code to execute"}
                },
                "required": ["code"]
            }
        }
    }
]

ALL_TOOLS = [execute_shell, execute_python]
```

## src/tools/base.py

```python
from langchain.tools import Tool

class BaseTool:
    """所有 Mason 工具的基类"""
    name: str
    description: str
    
    @staticmethod
    def run(*args, **kwargs):
        raise NotImplementedError("Tool must implement run method")
```

## src/tools/shell.py

```python
# import subprocess
from src.sandbox import get_sandbox

def execute_shell(command: str) -> str:
    sandbox = get_sandbox()
    return sandbox.execute(command)
```

## src/tools/python.py

```python
from src.sandbox import get_sandbox

def execute_python(code: str) -> str:
    sandbox = get_sandbox()
    return sandbox.execute_code(code, "python")
```

## src/web/app.py
```python
import uuid
import json
import re
import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from langchain_core.messages import HumanMessage, AIMessage

from src.graph.builder import build_graph
from src.db.memory import get_memory_store
from src.llm.provider import get_llm

# ✅ 修复：使用字符串路径，避免 Path 对象问题
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 全局变量（生产环境请用 Redis）
graphs = {}
stores = {}

def extract_memory_from_input(user_input, store):
    """独立记忆提取（与 CLI 版本一致）"""
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
    
    示例：
    输入："我叫Lucio，是个程序员，我喜欢蓝色"
    输出：{{"name": "Lucio", "job": "programmer", "like": "blue"}}
    
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
            namespace = ("user_profile",)
            for key, value in facts.items():
                if value and str(value).lower() != "none":
                    store.put(namespace, key, str(value))
    except:
        pass

# ✅ 修复：使用简单的 HTML 响应，避免模板缓存问题
@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    # 直接读取 HTML 文件，避免 Jinja2 缓存问题
    html_file = os.path.join(TEMPLATES_DIR, "index.html")
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Mason Web UI</title></head>
            <body>
                <h1>🦖 Mason Web UI</h1>
                <p>HTML 文件未找到，请检查 src/web/templates/index.html 是否存在。</p>
            </body>
        </html>
        """)

def run_graph_sync(graph, user_input, thread_id, websocket, loop):
    """Synchronous graph execution in a background thread"""
    try:
        for msg, metadata in graph.stream(
            {"messages": [HumanMessage(content=user_input)], "current_agent": "router"},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="messages"
        ):
            if isinstance(msg, AIMessage) and msg.content:
                content = msg.content
                # 过滤 JSON 垃圾
                if not (content.startswith("{") and content.endswith("}")):
                    # Send data to WebSocket via asyncio.run_coroutine_threadsafe
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "type": "stream",
                            "content": content
                        }),
                        loop
                    )
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            websocket.send_json({
                "type": "error",
                "content": str(e)
            }),
            loop
        )

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    # 为每个客户端创建独立的图和存储
    if client_id not in graphs:
        graphs[client_id] = build_graph()
        stores[client_id] = get_memory_store()
    
    graph = graphs[client_id]
    store = stores[client_id]
    thread_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    
    try:
        while True:
            data = await websocket.receive_text()
            user_input = json.loads(data)["message"]
            
            # 1. 独立记忆提取（不在图中）
            extract_memory_from_input(user_input, store)
            
            # 2. Start streaming
            await websocket.send_json({
                "type": "start",
                "content": ""
            })
            
            # 3. Run synchronous graph in a thread
            await loop.run_in_executor(None, run_graph_sync, graph, user_input, thread_id, websocket, loop)
            
            # 4. End streaming
            await websocket.send_json({
                "type": "end",
                "content": ""
            })
            
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "content": str(e)
        })

if __name__ == "__main__":
    import uvicorn
    
    # port = int(os.environ.get("PORT", 8080))
    port = 8080
    print(f"🦖 Mason Web UI 启动中...")
    print(f"📍 访问地址: http://localhost:{port}")
    print(f"🔌 WebSocket: ws://localhost:{port}/ws/{{client_id}}")
    
    uvicorn.run(
        app, 
        host="127.0.0.1",
        port=port,
        log_level="info"
    )
```
## src/web/templates/index.html
```python
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Mason Web UI</title>
    <link rel="stylesheet" href="/static/style.css">
    <style>
        /* 额外的样式，确保页面布局 */
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f2f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        header h1 {
            margin: 0;
            font-size: 24px;
        }
        header p {
            margin: 5px 0 0;
            opacity: 0.9;
        }
        .chat-box {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            border-bottom: 1px solid #eee;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 18px;
            max-width: 70%;
            word-wrap: break-word;
        }
        .user {
            background: #0084ff;
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 5px;
        }
        .assistant {
            background: #e4e6eb;
            color: #050505;
            margin-right: auto;
            border-bottom-left-radius: 5px;
        }
        .system, .error {
            background: #fff3cd;
            color: #856404;
            text-align: center;
            max-width: 100%;
            border-radius: 5px;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
        }
        .input-area {
            display: flex;
            padding: 20px;
        }
        .input-area input {
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 25px;
            outline: none;
            font-size: 16px;
        }
        .input-area button {
            margin-left: 10px;
            padding: 12px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
        }
        .input-area button:hover {
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🦖 Mason Stage 6</h1>
            <p>Web UI + WebSocket + Memory + Tools</p>
        </header>
        
        <div class="chat-box" id="chatBox">
            <!-- 消息会动态插入这里 -->
        </div>
        
        <div class="input-area">
            <input type="text" id="messageInput" placeholder="输入消息..." autofocus>
            <button onclick="sendMessage()">发送</button>
        </div>
    </div>

    <script>
        // 生成唯一的客户端ID
        const clientId = Math.random().toString(36).substring(2, 15);
        
        // 自动适配当前页面的协议和主机（解决跨域和连接问题）
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host; // 例如 localhost:8080
        const wsUrl = `${protocol}//${host}/ws/${clientId}`;
        
        let ws;
        let currentAssistantMessageDiv = null; // 用于追踪当前正在流式输出的消息元素

        function connectWebSocket() {
            console.log("尝试连接 WebSocket:", wsUrl);
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log("✅ WebSocket 连接成功");
                addMessage("system", "🦖 Mason 已连接！开始聊天吧 🚀");
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === "start") {
                        // 开始新的回复，创建新的消息元素
                        currentAssistantMessageDiv = addMessage("assistant", "");
                    } else if (data.type === "stream") {
                        // 追加内容到当前消息
                        if (currentAssistantMessageDiv) {
                            currentAssistantMessageDiv.textContent += data.content;
                            // 滚动到底部
                            const chatBox = document.getElementById("chatBox");
                            chatBox.scrollTop = chatBox.scrollHeight;
                        }
                    } else if (data.type === "end") {
                        // 流式结束，重置当前消息框
                        currentAssistantMessageDiv = null;
                    } else if (data.type === "error") {
                        // 显示错误信息
                        addMessage("error", "错误: " + data.content);
                    }
                } catch (e) {
                    console.error("解析消息失败:", e);
                    addMessage("error", "接收消息时发生错误。");
                }
            };

            ws.onerror = (error) => {
                console.error("❌ WebSocket 错误:", error);
                addMessage("error", "WebSocket 连接错误，请检查服务器是否运行。");
            };

            ws.onclose = () => {
                console.log("🔌 WebSocket 连接关闭");
                addMessage("system", "连接已断开，正在尝试重连...");
                // 可选：自动重连
                setTimeout(connectWebSocket, 3000);
            };
        }

        // 初始化连接
        connectWebSocket();

        function sendMessage() {
            const input = document.getElementById("messageInput");
            const message = input.value.trim();

            if (!message) return;
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                addMessage("error", "WebSocket 未连接，请稍后再试。");
                return;
            }

            // 显示用户消息
            addMessage("user", message);
            
            // 发送到 WebSocket
            ws.send(JSON.stringify({ message: message }));
            
            input.value = "";
        }

        function addMessage(sender, content) {
            const chatBox = document.getElementById("chatBox");
            const div = document.createElement("div");
            div.className = `message ${sender}`;
            div.textContent = content;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
            return div; // 返回创建的元素，方便后续操作
        }

        // 按 Enter 发送
        document.getElementById("messageInput").addEventListener("keypress", function(e) {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    </script>
</body>
</html>
```

## src/web/static/style.css

```css
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    margin: 0;
    padding: 20px;
    height: 100vh;
    box-sizing: border-box;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    border-radius: 15px;
    overflow: hidden;
    height: calc(100vh - 40px);
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}

header {
    background: linear-gradient(90deg, #667eea, #764ba2);
    color: white;
    padding: 20px;
    text-align: center;
}

header h1 {
    margin: 0;
    font-size: 24px;
}

header p {
    margin: 5px 0 0;
    opacity: 0.9;
}

.chat-box {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
}

.message {
    margin-bottom: 15px;
    padding: 12px 16px;
    border-radius: 18px;
    max-width: 70%;
    word-wrap: break-word;
}

.message.user {
    background: #667eea;
    color: white;
    margin-left: auto;
    border-bottom-right-radius: 5px;
}

.message.mason {
    background: #f0f0f0;
    color: #333;
    margin-right: auto;
    border-bottom-left-radius: 5px;
}

.message.system {
    background: #fff3cd;
    color: #856404;
    text-align: center;
    max-width: 100%;
}

.message.error {
    background: #f8d7da;
    color: #721c24;
    max-width: 100%;
}

.input-area {
    display: flex;
    padding: 20px;
    border-top: 1px solid #eee;
}

.input-area input {
    flex: 1;
    padding: 12px 16px;
    border: 2px solid #ddd;
    border-radius: 25px;
    outline: none;
    font-size: 16px;
}

.input-area button {
    margin-left: 10px;
    padding: 12px 24px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    color: white;
    border: none;
    border-radius: 25px;
    cursor: pointer;
    font-weight: bold;
}

.input-area button:hover {
    opacity: 0.9;
}
```

## 项目结构
```
│  LICENSE
│  README.md
│  requirements.txt
│
└─src
    │  main.py
    │  __init__.py
    │
    ├─agents
    │  │  base.py
    │  │  coder.py
    │  │  general.py
    │  │  __init__.py
    │
    ├─config
    │  │  settings.py
    │  │  __init__.py
    │
    ├─db
    │  │  memory.py
    │  │  __init__.py
    │
    ├─graph
    │  │  builder.py
    │  │  nodes.py
    │  │  state.py
    │  │  __init__.py
    │
    ├─llm
    │  │  provider.py
    │  │  __init__.py
    │
    ├─sandbox
    │  │  base.py
    │  │  docker_sandbox.py
    │  │  local_sandbox.py
    │  │  __init__.py
    │
    ├─tools
    │  │  base.py
    │  │  python.py
    │  │  shell.py
    │  │  __init__.py
    │
    ├─web
    │  │  app.py
    │  │
    │  ├─static
    │  │      style.css
    │  │
    │  ├─templates
    │  │      index.html
```