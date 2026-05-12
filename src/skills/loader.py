# src/skills/loader.py
import os
import importlib
import inspect
import yaml
from typing import Dict, List
from .base import BaseSkill

SKILL_DIR = os.path.join(os.path.dirname(__file__), "builtin")

class SkillLoader:
    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self.load_all()

    def load_all(self):
        print(f"🔍 Scanning for skills in: {SKILL_DIR}")
        
        for root, dirs, files in os.walk(SKILL_DIR):
            if "skill.yaml" in files:
                # 🆕 读取 skill.yaml
                yaml_path = os.path.join(root, "skill.yaml")
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    manifest = yaml.safe_load(f)
                
                skill_name = manifest.get("name")
                if not skill_name:
                    continue
                
                # 查找 main.py
                main_py = os.path.join(root, manifest.get("entry_point", "main.py"))
                if not os.path.exists(main_py):
                    print(f"❌ Entry point not found for {skill_name}")
                    continue
                
                # 动态导入
                relative_path = os.path.relpath(main_py, start=SKILL_DIR)
                module_name = "src.skills.builtin." + relative_path.replace(os.sep, ".")[:-3]
                
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                            skill_instance = obj()
                            # 🆕 注入权限配置
                            skill_instance.permissions = manifest.get("permissions", {})
                            self.skills[skill_name] = skill_instance
                            print(f"✅ Loaded Skill: {skill_name} (Permissions: {skill_instance.permissions})")
                except Exception as e:
                    print(f"❌ Failed to load skill {skill_name}: {e}")

    def get_all_schemas(self) -> List[Dict]:
        return [skill.get_schema() for skill in self.skills.values()]

    def get_skill(self, name: str) -> BaseSkill | None:
        return self.skills.get(name)

skill_loader = SkillLoader()