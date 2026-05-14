from src.skills.base import BaseSkill
from src.skills.builtin.reminder.main import SchedulerManager
from src.db import task_store
from pydantic import BaseModel, Field
from typing import List


class CancelReminderParams(BaseModel):
    task_id: str = Field(default="", description="要取消的任务ID（优先使用）。")
    task_description: str = Field(default="", description="要取消的任务描述（当没有task_id时使用）。")
    task_indices: List[int] = Field(default_factory=list, description="要取消的任务序号列表，例如 [1, 2, 4] 表示取消第1、2、4个任务。")
    cancel_all: bool = Field(default=False, description="是否取消所有定时任务。")


class CancelReminderSkill(BaseSkill):
    name = "cancel_reminder"
    description = "取消定时任务。支持按ID取消、按序号多选取消、取消全部。当用户说'取消任务'、'取消定时'、'取消所有任务'时激活。"
    args_schema = CancelReminderParams
    permissions = {"network": False, "filesystem": False, "max_cpu": 0.1, "max_memory": 32}

    def __init__(self):
        super().__init__()
        self.scheduler = SchedulerManager.get_instance()

    def execute(self, task_id: str = "", task_description: str = "",
                task_indices: List[int] = None, cancel_all: bool = False) -> str:
        try:
            if cancel_all:
                count = self.scheduler.cancel_all_jobs()
                if count > 0:
                    return f"✅ 已取消全部 {count} 个定时任务。"
                else:
                    return "📋 当前没有待取消的定时任务。"

            if task_indices:
                tasks = task_store.load_pending_tasks()
                if not tasks:
                    return "📋 当前没有待取消的定时任务。"

                results = []
                for idx in task_indices:
                    if 1 <= idx <= len(tasks):
                        t = tasks[idx - 1]
                        tid = t["id"]
                        success = self.scheduler.cancel_job(tid)
                        desc = t["task_description"]
                        if success:
                            results.append(f"✅ #{idx} {desc}")
                        else:
                            results.append(f"❌ #{idx} {desc}（取消失败）")
                    else:
                        results.append(f"⚠️ 序号 #{idx} 超出范围")

                return "\n".join(results)

            if task_id:
                success = self.scheduler.cancel_job(task_id)
                if success:
                    return f"✅ 已取消定时任务（ID: {task_id[:8]}）"
                else:
                    return f"❌ 未找到任务（ID: {task_id[:8]}），可能已执行或不存在"

            if task_description:
                return f'⚠️ 请提供任务ID来精确取消。你可以说"取消任务 {task_description}"，我会尝试匹配。'

            return "❌ 请提供要取消的任务ID、序号或描述。"
        except Exception as e:
            return f"❌ 取消失败: {str(e)}"