from .base import BaseAgent

CODER_PROMPT = """You are Mason's Coding Agent.
You are an expert software engineer.
You have access to tools to execute shell commands and python code.
Use tools whenever you need to verify code, list files, or run tests.
"""

class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(CODER_PROMPT)
        self.name = "coder"
        self.description = "Expert software engineer for coding tasks."