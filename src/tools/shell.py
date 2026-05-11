# import subprocess
from src.sandbox import get_sandbox

def execute_shell(command: str) -> str:
    sandbox = get_sandbox()
    return sandbox.execute(command)

# def execute_shell(command: str) -> str:
#     """执行 Shell 命令"""
#     try:
#         result = subprocess.run(
#             command,
#             shell=True,
#             capture_output=True,
#             text=True,
#             timeout=10
#         )
#         output = result.stdout + result.stderr
#         return output if output else "Command executed successfully (no output)."
#     except Exception as e:
#         return f"Error executing command: {str(e)}"

