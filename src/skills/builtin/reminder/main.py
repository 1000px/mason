import time
import threading
import dateparser
import json
from datetime import datetime
from src.skills.base import BaseSkill
from src.db import task_store
from pydantic import BaseModel, Field

task_queue = None

MSG_SCHEDULED = "__scheduled__"


def set_task_queue(q):
    global task_queue
    task_queue = q
    print("✅ [Reminder] 任务队列已连接。")


class SchedulerManager:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                t = threading.Thread(target=cls._instance._run, daemon=True)
                t.start()
            return cls._instance

    def __init__(self):
        self._timers: dict[str, threading.Timer] = {}

    def _run(self):
        while True:
            time.sleep(1)

    def add_job(self, run_time: datetime, payload: dict) -> str | None:
        now = datetime.now()
        delay = (run_time - now).total_seconds()
        if delay <= 0:
            return None

        task_id = task_store.save_task(run_time, payload.get("description", ""), payload)
        if not task_id:
            return None

        payload["_task_id"] = task_id
        t = threading.Timer(delay, self._trigger, args=[payload])
        t.daemon = True
        t.start()
        self._timers[task_id] = t
        return task_id

    def cancel_job(self, task_id: str) -> bool:
        timer = self._timers.pop(task_id, None)
        if timer is None:
            for key in list(self._timers.keys()):
                if key.startswith(task_id):
                    timer = self._timers.pop(key)
                    task_id = key
                    break
        if timer is not None:
            timer.cancel()
        return task_store.cancel_task(task_id)

    def cancel_all_jobs(self) -> int:
        count = 0
        for task_id, timer in list(self._timers.items()):
            timer.cancel()
            count += 1
        self._timers.clear()
        task_store.cancel_all_tasks()
        return count

    def _trigger(self, payload: dict):
        task_id = payload.pop("_task_id", None)
        if task_id:
            self._timers.pop(task_id, None)
            task_store.mark_triggered(task_id)

        task_desc = payload.get("description", "未知任务")
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔔 定时任务触发：{task_desc}", flush=True)

        if task_queue is not None:
            task_queue.put({"type": MSG_SCHEDULED, "payload": payload})
            print(f"✅ 任务已放入队列: {task_desc}", flush=True)
        else:
            print("❌ 错误：任务队列未初始化！", flush=True)

    def load_and_schedule(self):
        tasks = task_store.load_pending_tasks()
        restored = 0
        for t in tasks:
            run_time = t["run_time"]
            payload = t["task_payload"] or {}
            payload["description"] = t["task_description"]
            payload["_task_id"] = t["id"]

            now = datetime.now()
            delay = (run_time - now).total_seconds()
            if delay <= 0:
                task_store.mark_triggered(t["id"])
                if task_queue is not None:
                    task_queue.put({"type": MSG_SCHEDULED, "payload": payload})
                continue

            timer = threading.Timer(delay, self._trigger, args=[payload])
            timer.daemon = True
            timer.start()
            self._timers[t["id"]] = timer
            restored += 1

        if restored > 0:
            print(f"✅ [Reminder] 从 MySQL 恢复了 {restored} 个定时任务")


class ReminderParams(BaseModel):
    time_description: str = Field(description="时间描述，例如：'1分钟后'。")
    task_description: str = Field(description="要执行的任务描述。")
    task_payload: str = Field(default="{}", description="任务的具体参数JSON字符串。")


class ReminderSkill(BaseSkill):
    name = "reminder"
    description = "设置定时任务。时间到了会自动通知系统执行后续操作。"
    args_schema = ReminderParams
    permissions = {"network": False, "filesystem": False, "max_cpu": 0.2, "max_memory": 64}

    def __init__(self):
        super().__init__()
        self.scheduler = SchedulerManager.get_instance()

    def execute(self, time_description: str, task_description: str, task_payload: str = "{}") -> str:
        try:
            run_time = dateparser.parse(time_description, languages=['zh'])
            if not run_time:
                return "❌ 无法解析时间。"

            payload_dict = json.loads(task_payload)
            payload_dict["description"] = task_description

            task_id = self.scheduler.add_job(run_time, payload_dict)

            if task_id:
                return f"✅ 已设置定时任务（ID: {task_id[:8]}）：{time_description} 后将执行：{task_description}"
            else:
                return "❌ 设置失败，时间可能已过。"
        except Exception as e:
            return f"❌ 错误: {str(e)}"