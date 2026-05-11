import docker
import tempfile
import os
from .base import BaseSandbox

class DockerSandbox(BaseSandbox):
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.image = "python:3.11-slim"
            
            # 检查镜像是否存在，不存在才拉取
            images = self.client.images.list(name=self.image)
            if not images:
                print(f"Pulling image {self.image}...")
                self.client.images.pull(self.image)
                
        except Exception as e:
            raise RuntimeError(f"Docker not available: {e}")
    def execute(self, command: str) -> str:
        """
        在 Docker 容器中执行 Shell 命令
        """
        try:
            container = self.client.containers.run(
                image=self.image,
                command=["sh", "-c", command],
                remove=True,  # 自动删除容器
                detach=False,
                stdout=True,
                stderr=True,
                network_disabled=True,  # 🔒 禁用网络
                mem_limit="128m",       # 🔒 内存限制
                cpu_period=100000,
                cpu_quota=50000,        # 🔒 限制 CPU 50%
            )
            return container.decode("utf-8", errors="ignore")
        except Exception as e:
            return f"Docker Execution Error: {e}"

    def execute_code(self, code: str, language: str = "python") -> str:
        """
        在 Docker 中执行 Python 代码
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            fname = f.name
        
        try:
            container = self.client.containers.run(
                image=self.image,
                command=["python", "/app/script.py"],
                volumes={fname: {'bind': '/app/script.py', 'mode': 'ro'}}, # 只读挂载
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                network_disabled=True,
                mem_limit="128m",
            )
            return container.decode("utf-8", errors="ignore")
        finally:
            os.unlink(fname)