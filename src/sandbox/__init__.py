# src/sandbox/__init__.py
import logging
from src.config.settings import settings
from .local_sandbox import LocalSandbox
from .docker_sandbox import DockerSandbox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sandbox():
    """
    获取沙箱实例。
    如果配置了 Docker 但初始化失败，自动降级为 Local 沙箱。
    """
    if settings.SANDBOX_TYPE == "docker":
        try:
            sandbox = DockerSandbox()
            logger.info("✅ Docker Sandbox initialized successfully.")
            return sandbox
        except Exception as e:
            logger.warning(f"⚠️ Docker Sandbox failed: {e}. Falling back to Local Sandbox.")
            return LocalSandbox()
    
    return LocalSandbox()