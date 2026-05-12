# src/skills/loader.py
import os
import importlib
import inspect
from typing import Dict, List
from .base import BaseSkill

# 🔧 修复：递归扫描 builtin 目录及其子目录
SKILL_DIR = os.path.join(os.path.dirname(__file__), "builtin")

class SkillLoader:
    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self.load_all()

    def load_all(self):
        print(f"🔍 Scanning for skills in: {SKILL_DIR}")
        
        # 🆕 递归遍历所有子目录
        for root, dirs, files in os.walk(SKILL_DIR):
            for filename in files:
                if filename.endswith(".py") and not filename.startswith("__"):
                    # 构建模块路径
                    # 例如：src.skills.builtin.weather.main
                    relative_path = os.path.relpath(os.path.join(root, filename), start=SKILL_DIR)
                    module_name = "src.skills.builtin." + relative_path.replace(os.sep, ".")[:-3]  # 去掉 .py
                    
                    try:
                        module = importlib.import_module(module_name)
                        for name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                                skill_instance = obj()
                                self.skills[skill_instance.name] = skill_instance
                                print(f"✅ Loaded Skill: {skill_instance.name}")
                    except Exception as e:
                        print(f"❌ Failed to load skill from {filename}: {e}")

    def get_all_schemas(self) -> List[Dict]:
        return [skill.get_schema() for skill in self.skills.values()]

    def get_skill(self, name: str) -> BaseSkill | None:
        return self.skills.get(name)

skill_loader = SkillLoader()