# src/web/app.py
import uuid
import json
import re
import os
import asyncio
import threading  # 🆕 补上这个导入！
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.graph.builder import build_graph
from src.db.memory import get_memory_store
from src.llm.provider import get_llm

# ✅ 修复：使用标准的 os.path.join 拼接路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 全局变量（简易版，生产环境请用 Redis）
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

async def stream_to_websocket(websocket: WebSocket, graph, user_input: str, thread_id: str, loop: asyncio.AbstractEventLoop):
    """
    优化的流处理：使用 asyncio.Queue 解耦线程与协程
    """
    # 1. 创建异步队列
    queue = asyncio.Queue()
    
    # 2. 定义线程内的回调函数
    def thread_callback(msg_data):
        asyncio.run_coroutine_threadsafe(queue.put(msg_data), loop)
    
    try:
        # 发送开始信号
        await websocket.send_json({"type": "start"})
        
        # 3. 定义后台线程的工作函数
        def run_graph():
            try:
                for msg, meta in graph.stream(
                    {"messages": [HumanMessage(content=user_input)], "current_agent": "router"},
                    config={"configurable": {"thread_id": thread_id}},
                    stream_mode="messages"
                ):
                    # 只处理 AI 的消息内容，过滤掉工具调用的空内容
                    if isinstance(msg, AIMessage) and msg.content:
                        content = msg.content
                        # 过滤掉可能的 JSON 垃圾（如果 LLM 返回纯 JSON 工具调用）
                        if not (content.strip().startswith("{") and content.strip().endswith("}")):
                            thread_callback({"type": "stream", "content": content})
                    
                    # 如果想看工具调用状态，可以在这里加逻辑
                    # if isinstance(msg, ToolMessage):
                    #    thread_callback({"type": "tool_end", "content": "Tool done"})
                
                # 流结束
                thread_callback(None) 
                
            except Exception as e:
                thread_callback({"type": "error", "content": str(e)})
                thread_callback(None)
        
        # 4. 启动线程
        t = threading.Thread(target=run_graph, daemon=True)
        t.start()
        
        # 5. 异步消费队列
        while True:
            msg_data = await queue.get()
            if msg_data is None: # 结束信号
                break
            await websocket.send_json(msg_data)
        
        await websocket.send_json({"type": "end"})
        
    except WebSocketDisconnect:
        print(f"Client disconnected during stream")
    except Exception as e:
        await websocket.send_json({"type": "error", "content": str(e)})

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    
    if client_id not in graphs:
        graphs[client_id] = build_graph()
        stores[client_id] = get_memory_store()
    
    graph = graphs[client_id]
    store = stores[client_id]
    thread_id = str(uuid.uuid4())
    
    try:
        while True:
            data = await websocket.receive_text()
            user_input = json.loads(data)["message"]
            
            extract_memory_from_input(user_input, store)
            
            await stream_to_websocket(websocket, graph, user_input, thread_id, loop)
            
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")

# --- 路由部分 ---
@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    html_file = os.path.join(TEMPLATES_DIR, "index.html")
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Index not found</h1>")

# ... (保留 plugins API 等其他代码，确保路径拼接也是用 os.path.join) ...

if __name__ == "__main__":
    import uvicorn
    port = 8080
    print(f"🦖 Mason Web UI 启动中...")
    print(f"📍 访问地址: http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")