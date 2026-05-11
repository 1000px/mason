from langchain.tools import Tool

class BaseTool:
    """所有 Mason 工具的基类"""
    name: str
    description: str
    
    @staticmethod
    def run(*args, **kwargs):
        raise NotImplementedError("Tool must implement run method")