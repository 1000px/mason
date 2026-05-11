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
            # 尝试初始化 Docker 沙箱
            sandbox = DockerSandbox()
            logger.info("✅ Docker Sandbox initialized successfully.")
            return sandbox
        except Exception as e:
            # 关键：捕获所有异常，降级为 Local
            logger.warning(f"⚠️ Docker Sandbox failed: {e}. Falling back to Local Sandbox.")
            return LocalSandbox()
    
    # 如果不是 docker，直接用 local
    return LocalSandbox()