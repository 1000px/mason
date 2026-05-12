# src/skills/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel

class BaseSkill(ABC):
    name: str = "base_skill"
    description: str = "A base skill."
    args_schema: Type[BaseModel] = None 
    
    # 🆕 权限配置
    permissions: Dict[str, Any] = {
        "network": False,
        "filesystem": False,
        "max_cpu": 0.5,
        "max_memory": 128
    }

    @abstractmethod
    def execute(self, **kwargs) -> str:
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        properties = {}
        required = []
        
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
                    "required": required
                }
            }
        }