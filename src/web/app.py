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

# src/web/app.py
# ... 在原有代码的基础上，添加以下路由 ...

@app.get("/plugins", response_class=HTMLResponse)
async def plugins_page(request: Request):
    """插件市场页面"""
    html_file = os.path.join(TEMPLATES_DIR, "plugins.html")
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Plugin Market Not Found</h1>")

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

# src/web/app.py
# ... 原有代码保持不变 ...
import subprocess
import sys
import yaml
from pathlib import Path
import os

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# ---------- 🆕 插件市场 API ----------
@app.get("/api/plugins")
async def list_plugins():
    """列出所有已安装的插件及其权限"""
    plugins = []
    skills_dir = ROOT_DIR / "src" / "skills" / "builtin"
    
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("__"):
            manifest_path = skill_dir / "skill.yaml"
            if manifest_path.exists():
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = yaml.safe_load(f)
                    plugins.append({
                        "name": manifest.get("name"),
                        "display_name": manifest.get("display_name"),
                        "description": manifest.get("description"),
                        "version": manifest.get("version"),
                        "permissions": manifest.get("permissions", {}),
                        "status": "installed"
                    })
    return {"plugins": plugins}


@app.post("/api/plugins/install")
async def install_plugin(request: dict):
    """安装插件"""
    repo_url = request.get("repo_url")
    if not repo_url:
        return {"success": False, "error": "Repo URL is required"}
    
    print(f"🌐 Web UI: Installing plugin from: {repo_url}")
    
    script_path = ROOT_DIR / "install_skill.py"
    python_exe = sys.executable
    
    cmd = f'"{python_exe}" "{script_path}" "{repo_url}"'
    print(f"🔧 Executing command: {cmd}")
    
    try:
        # 🔧 修复：添加 encoding='utf-8'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',  # 🆕 强制使用 UTF-8 解码
            cwd=str(ROOT_DIR)
        )
        
        print(f"📤 Script stdout: {result.stdout}")
        if result.stderr:
            print(f"📤 Script stderr: {result.stderr}")
        
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr or result.stdout}
    except Exception as e:
        print(f"❌ Exception during installation: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/plugins/uninstall")
async def uninstall_plugin(request: dict):
    """卸载插件"""
    skill_name = request.get("skill_name")
    if not skill_name:
        return {"success": False, "error": "Skill name is required"}
    
    print(f"🌐 Web UI: Uninstalling plugin: {skill_name}")
    
    script_path = ROOT_DIR / "uninstall_skill.py"
    python_exe = sys.executable
    
    cmd = f'"{python_exe}" "{script_path}" "{skill_name}"'
    print(f"🔧 Executing command: {cmd}")
    
    try:
        # 🔧 修复：添加 encoding='utf-8'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',  # 🆕 强制使用 UTF-8 解码
            cwd=str(ROOT_DIR)
        )
        
        print(f"📤 Script stdout: {result.stdout}")
        if result.stderr:
            print(f"📤 Script stderr: {result.stderr}")
        
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr or result.stdout}
    except Exception as e:
        print(f"❌ Exception during uninstallation: {e}")
        return {"success": False, "error": str(e)}

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