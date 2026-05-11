import subprocess
import tempfile
import os
from .base import BaseSandbox
from src.config.settings import settings

class LocalSandbox(BaseSandbox):
    def execute(self, command: str) -> str:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=10
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Execution Error: {e}"

    def execute_code(self, code: str, language: str = "python") -> str:
        if language != "python":
            return "Only python supported in local sandbox."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            fname = f.name
        
        try:
            result = subprocess.run(
                ["python", fname], capture_output=True, text=True, timeout=settings.SANDBOX_TIMEOUT
            )
            return result.stdout + result.stderr
        finally:
            os.unlink(fname)