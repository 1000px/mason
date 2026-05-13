# src/skills/loader.py
import os
import logging
import importlib
import inspect
import yaml
from typing import Dict, List, Optional

from .base import BaseSkill
from .script_skill import ScriptSkill

logger = logging.getLogger(__name__)

BUILTIN_SKILL_DIR = os.path.join(os.path.dirname(__file__), "builtin")
USER_SKILL_DIR = os.path.join(os.path.dirname(__file__), "user")

DEFAULT_ENTRY_POINTS = {
    "python": "main.py",
    "javascript": "main.js",
    "shell": "main.sh",
}


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

    def _load_python_skill(self, manifest: dict, skill_name: str, root: str, base_dir: str):
        entry_point = manifest.get("entry_point", "main.py")
        main_py = os.path.join(root, entry_point)
        if not os.path.isfile(main_py):
            logger.warning("Entry point not found for %s: %s", skill_name, main_py)
            return

        module_name = self._resolve_module_name(main_py, base_dir)
        if module_name is None:
            logger.warning("Could not resolve module name for %s", skill_name)
            return

        module = importlib.import_module(module_name)
        skill_instance = None
        for _name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseSkill)
                and obj is not BaseSkill
                and obj is not ScriptSkill
            ):
                skill_instance = obj()
                break

        if skill_instance is None:
            logger.warning("No BaseSkill subclass found in %s", skill_name)
            return

        skill_instance.permissions = manifest.get("permissions", {})

        if not skill_instance.validate():
            logger.warning("Skill %s failed validation", skill_name)
            return

        skill_instance.setup()
        self._skills[skill_name] = skill_instance
        logger.info(
            "Loaded python skill: %s (permissions: %s)",
            skill_name,
            skill_instance.permissions,
        )

    def _load_script_skill(self, manifest: dict, skill_name: str, root: str, runtime: str):
        entry_point = manifest.get("entry_point", DEFAULT_ENTRY_POINTS.get(runtime, "main.js"))
        script_path = os.path.join(root, entry_point)
        if not os.path.isfile(script_path):
            logger.warning("Script not found for %s: %s", skill_name, script_path)
            return

        description = manifest.get("description", "")
        parameters_schema = manifest.get("parameters", {})
        permissions = manifest.get("permissions", {})

        skill_instance = ScriptSkill(
            name=skill_name,
            description=description,
            script_path=script_path,
            runtime=runtime,
            parameters_schema=parameters_schema,
            permissions=permissions,
        )

        if not skill_instance.validate():
            logger.warning("Script skill %s failed validation", skill_name)
            return

        skill_instance.setup()
        self._skills[skill_name] = skill_instance
        logger.info(
            "Loaded %s skill: %s (script: %s)",
            runtime,
            skill_name,
            script_path,
        )

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

                runtime = manifest.get("runtime", "python")

                try:
                    if runtime == "python":
                        self._load_python_skill(manifest, skill_name, root, base_dir)
                    elif runtime in ("javascript", "shell"):
                        self._load_script_skill(manifest, skill_name, root, runtime)
                    else:
                        logger.warning("Unknown runtime '%s' for skill %s", runtime, skill_name)
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