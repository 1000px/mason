from .shell import execute_shell
from .python import execute_python

# 工具注册表（不用 Tool 类）
TOOLS_REGISTRY = {
    "execute_shell": execute_shell,
    "execute_python": execute_python
}

# 工具定义（给 LLM 看的 Schema）
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Execute a shell command. Use this to interact with the file system, run scripts, or manage processes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "Execute Python code. Use this for calculations, data processing, or complex logic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The Python code to execute"}
                },
                "required": ["code"]
            }
        }
    }
]