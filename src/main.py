# src/main.py
import logging
import sys
import os
import json
import uuid
import queue
import threading
import time
from datetime import datetime

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 关闭所有第三方库的 INFO / DEBUG 日志，保持输出整洁
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("langgraph").setLevel(logging.WARNING)

from langchain_core.messages import HumanMessage
from src.graph.builder import build_graph
from src.db.memory import get_memory_store
from src.llm.provider import get_llm

# --- 🚀 全局队列 (连接 Reminder 子线程和主循环) ---
TASK_QUEUE = queue.Queue()
should_exit = False

# 队列消息类型标记
MSG_USER_INPUT = "__user_input__"
MSG_SCHEDULED = "__scheduled__"


def input_thread_worker():
    while not should_exit:
        try:
            user_input = input()
            if should_exit:
                break
            TASK_QUEUE.put({"type": MSG_USER_INPUT, "content": user_input})
        except EOFError:
            TASK_QUEUE.put({"type": MSG_USER_INPUT, "content": "exit"})
            break
        except Exception:
            break
# --- 辅助函数 ---
def extract_memory_from_input(user_input, store):
    """从用户输入中提取记忆（独立函数，不在图中）"""
    namespace = ("user_profile",)
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
            import re
            json_match = re.search(r'\{.*\}', res.content, re.DOTALL)
            if json_match:
                facts = json.loads(json_match.group())
        
        if facts:
            for key, value in facts.items():
                if value and str(value).lower() != "none":
                    store.put(namespace, key, str(value))
    except Exception:
        pass

def put_task_into_queue(payload: dict):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 (Callback) 定时任务入队: {payload.get('description')}", flush=True)
    TASK_QUEUE.put({"type": MSG_SCHEDULED, "payload": payload})

def process_input(user_input: str, config: dict):
    """
    核心处理函数：将输入交给 LangGraph 处理，并流式输出结果。
    """
    inputs = {"messages": [HumanMessage(content=user_input)]}
    try:
        # 使用 stream_mode="messages" 来逐字输出 AI 的回复
        # 同时也监控工具调用
        for chunk, meta in graph.stream(inputs, config=config, stream_mode="messages"):
            if hasattr(chunk, 'content') and chunk.content:
                print(chunk.content, end="", flush=True)
        print() # 流式结束后换行
    except Exception as e:
        print(f"\n❌ Error during processing: {e}", flush=True)

# --- 初始化 Graph ---
# 必须在主线程初始化，避免某些库的多线程问题
graph = build_graph()

def main():
    global should_exit
    print("🦖 Mason Agent's AI Studio Working ...\n")
    
    # 初始化存储和配置
    store = get_memory_store()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # 🆕🆕🆕 关键步骤：把主程序的队列"安装"到 reminder 模块里 🆕🆕🆕
    try:
        from src.skills.builtin.reminder.main import set_task_queue
        set_task_queue(TASK_QUEUE)
        print("✅ Reminder 队列注入成功！")
    except Exception as e:
        print(f"❌ 注入队列失败: {e}")

    print("-" * 40)
    print("💡 提示：输入 'exit' 退出。")
    print("💡 定时任务触发时，会自动在此处执行。")
    print("-" * 40)

    try:
        input_thread = threading.Thread(target=input_thread_worker, daemon=True)
        input_thread.start()

        while True:
            msg = TASK_QUEUE.get()

            if msg["type"] == MSG_USER_INPUT:
                user_input = msg["content"]
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    print("👋 Goodbye!", flush=True)
                    should_exit = True
                    break

                extract_memory_from_input(user_input, store)

                print("Mason: ", end="", flush=True)
                process_input(user_input, config)

            elif msg["type"] == MSG_SCHEDULED:
                task_payload = msg["payload"]
                desc = task_payload.get("description", "")
                payload_str = json.dumps(task_payload, ensure_ascii=False)

                instruction = f"System: 请执行以下定时任务：{desc}。具体参数：{payload_str}"

                print(f"\n� [Main] 检测到定时任务，唤醒 Mason...", flush=True)
                print("Mason: ", end="", flush=True)

                process_input(instruction, config)

            TASK_QUEUE.task_done()
            print("You: ", end="", flush=True)
                
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.stdout.flush()
    finally:
        should_exit = True
        print("Mason 已关闭。")
        sys.stdout.flush()

if __name__ == "__main__":
    main()