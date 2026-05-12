# src/skills/loader.py
import os
import importlib
import inspect
from typing import Dict, List
from .base import BaseSkill

SKILL_DIR = os.path.join(os.path.dirname(__file__), "builtin")

class SkillLoader:
    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self.load_all()

    def load_all(self):
        print(f"🔍 Scanning for skills in: {SKILL_DIR}")
        for filename in os.listdir(SKILL_DIR):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"src.skills.builtin.{filename[:-3]}"
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