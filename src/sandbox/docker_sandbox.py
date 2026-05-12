# src/sandbox/docker_sandbox.py
import docker
import os
import tempfile
from typing import Dict, Any
from .base import BaseSandbox

class DockerSandbox(BaseSandbox):
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.image = "mason-skill-sandbox"
            self.host_workspace = os.path.abspath("./workspace")
            os.makedirs(self.host_workspace, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Docker Sandbox init failed: {e}")

    def _run_container(self, command: str, permissions: Dict[str, Any]) -> str:
        """根据权限动态配置容器"""
        try:
            # 从权限字典获取配置
            network_allowed = permissions.get("network", False)
            fs_allowed = permissions.get("filesystem", False)
            max_cpu = int(permissions.get("max_cpu", 0.5) * 100000)
            max_memory = f"{permissions.get('max_memory', 128)}m"

            # 动态挂载卷
            volumes = {}
            if fs_allowed:
                volumes[self.host_workspace] = {'bind': '/workspace', 'mode': 'rw'}
            else:
                # 如果不允许文件系统，挂载为空
                volumes = {}

            container = self.client.containers.run(
                image=self.image,
                command=["sh", "-c", command],
                volumes=volumes,
                working_dir="/workspace" if fs_allowed else "/tmp",
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                # 动态权限
                network_disabled=not network_allowed,
                privileged=False,
                user="app",
                mem_limit=max_memory,
                cpu_period=100000,
                cpu_quota=max_cpu,
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],
                read_only=not fs_allowed,
                tmpfs={"/tmp": "size=64m"} if not fs_allowed else None,
            )
            return container.decode("utf-8", errors="ignore")
        except Exception as e:
            return f"Docker Sandbox Error: {e}"

    def execute(self, command: str, permissions: Dict[str, Any] = None) -> str:
        """执行 Shell 命令（带权限）"""
        if permissions is None:
            permissions = {"network": False, "filesystem": False}
        
        dangerous = ["rm -rf", "mkfs", "dd", "chmod 777"]
        if any(cmd in command for cmd in dangerous):
            return "🚨 Command blocked by sandbox."
        return self._run_container(command, permissions)

    def execute_code(self, code: str, language: str = "python", permissions: Dict[str, Any] = None) -> str:
        """执行代码（带权限）"""
        if permissions is None:
            permissions = {"network": False, "filesystem": False}

        # 👉 1. 打印进来的权限，确认网络确实是开放的
        # print(f"🐛 [Sandbox Debug] Received permissions: {permissions}") 

        if language != "python":
            return "Only python supported in docker sandbox."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            host_script_path = f.name
        
        try:
            # 动态挂载卷
            volumes = {
                host_script_path: {'bind': '/tmp/script.py', 'mode': 'ro'}
            }
            if permissions.get("filesystem", False):
                volumes[self.host_workspace] = {'bind': '/workspace', 'mode': 'rw'}
            
            container = self.client.containers.run(
                image=self.image,
                command=["python", "/tmp/script.py"],
                volumes=volumes,
                working_dir="/workspace" if permissions.get("filesystem", False) else "/tmp",
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                network_disabled=not permissions.get("network", False),
                user="app",
                mem_limit=f"{permissions.get('max_memory', 128)}m",
                cpu_period=100000,
                cpu_quota=int(permissions.get("max_cpu", 0.5) * 100000),
                read_only=not permissions.get("filesystem", False),
                tmpfs={"/tmp": "size=64m"},
            )
            result = container.decode("utf-8", errors="ignore")
            # 👉 2. 打印容器原本的输出
            # print(f"🐛 [Sandbox Debug] Container raw output: '{result}'")

            return result
        except Exception as e:
            # 👉 3. 如果这里出错，把具体的错误抛出来
            error_msg = f"Docker Execution Error: {e}" 
            # print(f"🐛 [Sandbox Debug] {error_msg}")
            return error_msg
        finally:
            os.unlink(host_script_path)