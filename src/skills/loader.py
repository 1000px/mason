# src/skills/loader.py
import os
import logging
import importlib
import inspect
import yaml
from typing import Dict, List, Optional

from .base import BaseSkill

logger = logging.getLogger(__name__)

BUILTIN_SKILL_DIR = os.path.join(os.path.dirname(__file__), "builtin")
USER_SKILL_DIR = os.path.join(os.path.dirname(__file__), "user")


class SkillLoader:
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._manifests: Dict[str, dict] = {}
        self._skill_dirs: Dict[str, str] = {}
        self._load_all()

    def _get_scan_dirs(self) -> List[str]:
        dirs = [BUILTIN_SKILL_DIR]
        if os.path.isdir(USER_SKILL_DIR):
            dirs.append(USER_SKILL_DIR)
        return dirs

    def _resolve_module_name(self, main_py: str, base_dir: str) -> Optional[str]:
        try:
            relative_path = os.path.relpath(main_py, start=base_dir)
        except ValueError:
            return None

        if base_dir == BUILTIN_SKILL_DIR:
            prefix = "src.skills.builtin"
        else:
            prefix = "src.skills.user"

        module_path = relative_path.replace(os.sep, ".")[:-3]
        return f"{prefix}.{module_path}"

    def _load_all(self):
        logger.info("Scanning for skills...")

        for base_dir in self._get_scan_dirs():
            if not os.path.isdir(base_dir):
                continue

            for root, dirs, files in os.walk(base_dir):
                if "skill.yaml" not in files:
                    continue

                yaml_path = os.path.join(root, "skill.yaml")
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        manifest = yaml.safe_load(f)
                except Exception as e:
                    logger.warning("Failed to read %s: %s", yaml_path, e)
                    continue

                skill_name = manifest.get("name")
                if not skill_name:
                    continue

                self._manifests[skill_name] = manifest
                self._skill_dirs[skill_name] = root

                main_py = os.path.join(root, manifest.get("entry_point", "main.py"))
                if not os.path.isfile(main_py):
                    logger.warning("Entry point not found for %s", skill_name)
                    continue

                module_name = self._resolve_module_name(main_py, base_dir)
                if module_name is None:
                    logger.warning("Could not resolve module name for %s", skill_name)
                    continue

                try:
                    module = importlib.import_module(module_name)
                    skill_instance = None
                    for _name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, BaseSkill)
                            and obj is not BaseSkill
                        ):
                            skill_instance = obj()
                            break

                    if skill_instance is None:
                        logger.warning("No BaseSkill subclass found in %s", skill_name)
                        continue

                    skill_instance.permissions = manifest.get("permissions", {})

                    if not skill_instance.validate():
                        logger.warning("Skill %s failed validation", skill_name)
                        continue

                    skill_instance.setup()
                    self._skills[skill_name] = skill_instance
                    logger.info(
                        "Loaded skill: %s (permissions: %s)",
                        skill_name,
                        skill_instance.permissions,
                    )
                except Exception as e:
                    logger.error("Failed to load skill %s: %s", skill_name, e)

    def get_all_schemas(self) -> List[Dict]:
        schemas = []
        for skill in self._skills.values():
            schemas.append(skill.get_schema())
        return schemas

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def get_manifest(self, name: str) -> Optional[dict]:
        return self._manifests.get(name)

    def list_skills(self) -> List[str]:
        return list(self._skills.keys())

    def reload(self):
        for skill in self._skills.values():
            try:
                skill.teardown()
            except Exception as e:
                logger.warning("Teardown failed for %s: %s", skill.name, e)
        self._skills.clear()
        self._manifests.clear()
        self._skill_dirs.clear()
        self._load_all()


skill_loader = SkillLoader()