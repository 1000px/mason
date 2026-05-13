# src/skills/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel


class BaseSkill(ABC):
    name: str = "base_skill"
    description: str = "A base skill."
    args_schema: Optional[Type[BaseModel]] = None

    permissions: Dict[str, Any] = {
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
        return True

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        pass

    def get_schema(self) -> Dict[str, Any]:
        properties: Dict[str, Any] = {}
        required: list[str] = []

        if self.args_schema:
            schema = self.args_schema.model_json_schema()
            properties = schema.get("properties", {})
            required = schema.get("required", [])

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