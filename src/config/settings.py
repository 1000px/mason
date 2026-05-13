import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ACTIVE_PROVIDER: str = os.getenv("ACTIVE_MODEL_PROVIDER", "deepseek")
    
    # DeepSeek Config
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    
    # Qwen Config
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    # NVIDIA Config
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

    # 🆕 Sandbox Config
    SANDBOX_TYPE: str = "docker" # 写死，不允许local模式
    SANDBOX_TIMEOUT: int = int(os.getenv("SANDBOX_TIMEOUT", "10"))  # seconds
    # MySQL Config
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "3306"))
    USER: str = os.getenv("USER", "root")
    PASSWORD: str = os.getenv("PASSWORD", "")
    DATABASE: str = os.getenv("DATABASE", "mason")
    CHARSET: str = os.getenv("CHARSET", "utf8mb4")

settings = Settings()