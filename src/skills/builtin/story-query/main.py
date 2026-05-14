from src.skills.base import BaseSkill
from src.db.story_store import query_available_stories, count_available_stories


class StoryQuerySkill(BaseSkill):
    name = "story_query"
    description = "查询数据库中可用的故事列表（status=0），返回标题、作者、标签、收集时间。"

    permissions = {
        "network": False,
        "filesystem": False,
        "max_cpu": 0.2,
        "max_memory": 64,
    }

    def execute(self, **kwargs) -> str:
        total = count_available_stories()
        if total == 0:
            return "📋 当前没有可用的故事。"

        stories = query_available_stories()

        lines = [f"📋 当前共有 {total} 个可用故事：\n"]
        for i, s in enumerate(stories, 1):
            tags_display = s["tags"] if s["tags"] else "—"
            lines.append(
                f"{i}. 《{s['title']}》 | 作者：{s['author']} | "
                f"标签：{tags_display} | 收集时间：{s['collected_at']}"
            )

        return "\n".join(lines)


def create_skill():
    return StoryQuerySkill()