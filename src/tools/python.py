# import sys
# import io
from src.sandbox import get_sandbox

def execute_python(code: str) -> str:
    sandbox = get_sandbox()
    return sandbox.execute_code(code, "python")

# def execute_python(code: str) -> str:
#     """执行 Python 代码"""
#     try:
#         old_stdout = sys.stdout
#         old_stderr = sys.stderr
#         new_stdout = io.StringIO()
#         new_stderr = io.StringIO()
#         sys.stdout = new_stdout
#         sys.stderr = new_stderr
        
#         exec(code)
        
#         sys.stdout = old_stdout
#         sys.stderr = old_stderr
        
#         output = new_stdout.getvalue() + new_stderr.getvalue()
#         return output if output else "Code executed successfully (no output)."
#     except Exception as e:
#         sys.stdout = old_stdout
#         sys.stderr = old_stderr
#         return f"Error executing python code: {str(e)}"

# python_tool = Tool(
#     name="execute_python",
#     func=execute_python,
#     description="Execute Python code. Use this for calculations, data processing, or complex logic."
# )