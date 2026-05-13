from langchain_openai import ChatOpenAI
from src.config.settings import settings

def get_llm(model_name: str | None = None):
    """
    根据配置动态返回 LLM 实例
    """
    provider = settings.ACTIVE_PROVIDER
    
    if provider == "deepseek":
        return ChatOpenAI(
            model=model_name or "deepseek-chat",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0.7,
        )
    elif provider == "qwen":
        return ChatOpenAI(
            model=model_name or "qwen-plus",
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.DASHSCOPE_BASE_URL,
            temperature=0.7,
        )
    elif provider == "nvidia":
        return ChatOpenAI(
            model=model_name or "deepseek-ai/deepseek-v4-pro",
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.7,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")