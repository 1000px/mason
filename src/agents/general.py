from .base import BaseAgent

GENERAL_PROMPT = """You are Mason, a helpful general assistant.
You are good at chatting, summarizing, and answering general questions.
If you don't know the answer, just say so.
"""

class GeneralAgent(BaseAgent):
    def __init__(self):
        super().__init__(GENERAL_PROMPT)
        self.name = "general"
        self.description = "General assistant for chatting, summarizing, and answering general questions."