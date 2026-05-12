# src/skills/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel

class BaseSkill(ABC):
    name: str = "base_skill"
    description: str = "A base skill."
    args_schema: Type[BaseModel] = None 

    @abstractmethod
    def execute(self, **kwargs) -> str:
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """返回给 LangChain/LangGraph 的工具 schema"""
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