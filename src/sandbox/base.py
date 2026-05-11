from abc import ABC, abstractmethod

class BaseSandbox(ABC):
    @abstractmethod
    def execute(self, command: str) -> str:
        """执行命令并返回结果"""
        pass

    @abstractmethod
    def execute_code(self, code: str, language: str = "python") -> str:
        """执行代码并返回结果"""
        pass