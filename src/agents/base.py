from langchain_core.prompts import ChatPromptTemplate
from src.llm.provider import get_llm

class BaseAgent:
    def __init__(self, system_prompt: str):
        self.base_prompt = system_prompt
        self.llm = get_llm()