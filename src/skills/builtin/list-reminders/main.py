from src.skills.base import BaseSkill
from src.db import task_store
from pydantic import BaseModel


class ListRemindersParams(BaseModel):
    pass


class ListRemindersSkill(BaseSkill):
    name = "list_reminders"
    description = "列出当前所有待执行的定时任务。"
    args_schema = ListRemindersParams
    permissions = {"network": False, "filesystem": False, "max_cpu": 0.1, "max_memory": 32}

    def execute(self) -> str:
        try:
            tasks = task_store.load_pending_tasks()
            if not tasks:
                return "📋 当前没有待执行的定时任务。"

            lines = ["📋 当前定时任务列表："]
            for i, t in enumerate(tasks, 1):
                task_id = t["id"][:8]
                run_time = t["run_time"]
                if hasattr(run_time, 'strftime'):
                    time_str = run_time.strftime('%Y-%m-%d %H:%M')
                else:
                    time_str = str(run_time)
                desc = t["task_description"]
                lines.append(f"{i}. [ID: {task_id}] {time_str} - {desc}")

            return "\n" + "\n".join(lines) + "\n\n"

        except Exception as e:
            return f"❌ 查询失败: {str(e)}"