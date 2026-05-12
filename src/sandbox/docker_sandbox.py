# src/sandbox/docker_sandbox.py
import docker
import os
import tempfile
from .base import BaseSandbox

class DockerSandbox(BaseSandbox):
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.image = "mason-skill-sandbox"
            
            # 确保镜像存在
            images = self.client.images.list(name=self.image)
            if not images:
                raise RuntimeError(f"Image {self.image} not found. Please build it first.")
                
            # 🔒 定义宿主机的工作区（绝对路径）
            self.host_workspace = os.path.abspath("./workspace")
            os.makedirs(self.host_workspace, exist_ok=True)
            
        except Exception as e:
            raise RuntimeError(f"Docker Sandbox init failed: {e}")
    
    def _clean_output(self, output: str) -> str:
        """清理 Docker 容器的输出"""
        # 移除 ANSI 颜色代码
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ansi_escape.sub('', output)
        # 只保留第一行（防止多余输出）
        return output.strip().split('\n')[0]

    def _run_container(self, command: str, allow_network: bool = False) -> str:
        """
        🔒 核心执行方法：在严格受限的容器中运行命令
        allow_network: 是否允许该 Skill 联网，默认 False
        """
        try:
            # 🔒 动态决定是否断网
            network_setting = not allow_network  # 如果 allow_network=True，则 network_disabled=False

            # 🔒 关键安全配置
            container = self.client.containers.run(
                image=self.image,
                command=["sh", "-c", command],
                # 🔒 挂载宿主机 workspace 到容器 /workspace (只读挂载，除非特别需要写)
                volumes={
                    self.host_workspace: {
                        'bind': '/workspace',
                        'mode': 'rw'  # 如果需要写权限，设为 rw；否则 ro
                    }
                },
                working_dir="/workspace",  # 锁定工作目录
                remove=True,  # 自动删除容器
                detach=False,
                stdout=True,
                stderr=True,
                # 🔒 安全隔离配置
                network_disabled=True,  # 断网, 禁止访问外部网络
                privileged=False,        # 禁止特权模式
                user="app",             # 非 root 用户
                mem_limit="128m",       # 内存限制
                cpu_period=100000,
                cpu_quota=50000,        # 限制 CPU 50%
                security_opt=["no-new-privileges"],  # 禁止提权
                cap_drop=["ALL"],        # 丢弃所有 Linux 权限
                read_only=True,         # 🔒 根文件系统只读
                tmpfs={"/tmp": "size=64m"},  # 仅允许 /tmp 可写
            )
            return container.decode("utf-8", errors="ignore")
            # 在返回前调用
            # output = container.decode("utf-8", errors="ignore")
            # return self._clean_output(output)
        except Exception as e:
            return f"Docker Sandbox Error: {e}"

    def execute(self, command: str) -> str:
        """
        执行 Shell 命令
        """
        # 🔒 防御性编程：禁止危险命令
        dangerous = ["rm -rf", "mkfs", "dd", "chmod 777"]
        if any(cmd in command for cmd in dangerous):
            return "🚨 Command blocked by sandbox for security reasons."
        return self._run_container(command)

    def execute_code(self, code: str, language: str = "python", allow_network: bool = False) -> str:
        """
        执行代码（通过写入临时文件再执行）
        """
        if language != "python":
            return "Only python supported in docker sandbox."
        
        # 在容器内创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            host_script_path = f.name
        
        try:
            # 将宿主机临时文件挂载到容器内执行
            container = self.client.containers.run(
                image=self.image,
                command=["python", "/tmp/script.py"],
                volumes={
                    self.host_workspace: {'bind': '/workspace', 'mode': 'rw'},
                    host_script_path: {'bind': '/tmp/script.py', 'mode': 'ro'}
                },
                working_dir="/workspace",
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                network_disabled=not allow_network,
                user="app",
                mem_limit="128m",
                read_only=True,
                tmpfs={"/tmp": "size=64m"},
            )
            return container.decode("utf-8", errors="ignore")
        finally:
            os.unlink(host_script_path)