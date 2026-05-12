# src/skills/builtin/file_manager.py
import os
import re
from pydantic import BaseModel, Field
from src.skills.base import BaseSkill
from src.sandbox import get_sandbox

class FileManagerArgs(BaseModel):
    action: str = Field(description="Action: 'read', 'write', 'list'.")
    path: str = Field(description="Relative path inside /workspace (e.g., 'data/test.txt').")
    content: str = Field(default="", description="Content to write.")

class FileManagerSkill(BaseSkill):
    name = "file_manager"
    description = "Manages files ONLY within the /workspace directory using a secure Docker sandbox."
    args_schema = FileManagerArgs
    
    def __init__(self):
        super().__init__()
        self.sandbox = get_sandbox()
        print(f"🛡️ FileManagerSkill loaded with Docker Sandbox.")

    def _sanitize_path(self, path: str) -> str:
        path = path.lstrip('/')
        if '..' in path:
            raise ValueError("Path traversal detected.")
        return path

    def execute(self, action: str, path: str, content: str = "") -> str:
        try:
            safe_path = self._sanitize_path(path)
            
            if action == "list":
                cmd = f"ls -la {safe_path}"
                return self.sandbox.execute(cmd)
            
            elif action == "read":
                cmd = f"cat {safe_path}"
                return self.sandbox.execute(cmd)
            
            elif action == "write":
                dir_part = os.path.dirname(safe_path)
                if dir_part:
                    self.sandbox.execute(f"mkdir -p {dir_part}")
                
                python_code = f"""
import sys
with open('{safe_path}', 'w', encoding='utf-8') as f:
    f.write('''{content}''')
print('Write success')
"""
                result = self.sandbox.execute_code(python_code)
                if "Write success" in result:
                    return f"Successfully wrote to {safe_path}"
                else:
                    return f"Write failed: {result}"
            
            else:
                return f"Error: Unknown action '{action}'."
        
        except Exception as e:
            return f"🚨 Skill Error: {str(e)}"
