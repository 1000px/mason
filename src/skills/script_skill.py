import subprocess
import json
import logging
import platform
from typing import Dict, Any, Optional

from .base import BaseSkill

logger = logging.getLogger(__name__)

RUNTIME_COMMANDS = {
    "javascript": ["node"],
    "shell": ["bash"],
}


class ScriptSkill(BaseSkill):
    def __init__(
        self,
        name: str,
        description: str,
        script_path: str,
        runtime: str,
        parameters_schema: Optional[Dict[str, Any]] = None,
        permissions: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self._script_path = script_path
        self._runtime = runtime
        self._parameters_schema = parameters_schema or {}
        self.permissions = permissions or {
            "network": False,
            "filesystem": False,
            "max_cpu": 0.5,
            "max_memory": 128,
        }

    def validate(self) -> bool:
        if not self.name or self.name == "base_skill":
            return False
        if not self.description:
            return False
        if self._runtime not in RUNTIME_COMMANDS:
            logger.warning("Unsupported runtime: %s", self._runtime)
            return False
        return True

    @staticmethod
    def _to_wsl_path(windows_path: str) -> str:
        drive = windows_path[0].lower()
        rest = windows_path[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"

    def _build_cmd(self) -> list:
        runtime_cmd = RUNTIME_COMMANDS[self._runtime]

        if self._runtime == "shell" and platform.system() == "Windows":
            wsl_path = self._to_wsl_path(self._script_path)
            return ["wsl", "bash", wsl_path]

        return runtime_cmd + [self._script_path]

    def execute(self, **kwargs) -> str:
        cmd = self._build_cmd()

        input_json = json.dumps(kwargs, ensure_ascii=False)

        try:
            result = subprocess.run(
                cmd,
                input=input_json,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            if result.returncode != 0:
                error_msg = stderr or stdout or "Unknown error"
                return f"❌ 脚本执行失败 (exit code {result.returncode}): {error_msg}"

            return stdout

        except subprocess.TimeoutExpired:
            return "❌ 脚本执行超时（30秒）"
        except FileNotFoundError:
            return f"❌ 运行时未找到: {' '.join(cmd)}。请确保已安装。"
        except Exception as e:
            return f"❌ 脚本执行异常: {str(e)}"

    def get_schema(self) -> Dict[str, Any]:
        properties: Dict[str, Any] = {}
        required: list[str] = []

        for param_name, param_def in self._parameters_schema.items():
            properties[param_name] = {
                "type": param_def.get("type", "string"),
                "description": param_def.get("description", ""),
            }
            if param_def.get("required", False):
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }