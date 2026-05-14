# src/skills/builtin/news_fetcher/main.py
import os
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field
from src.sandbox import get_sandbox

class NewsFetcherArgs(BaseModel):
    count: int = Field(default=5, description="要抓取的新闻条数。")

class NewsFetcherSkill(BaseSkill):
    name = "news-fetcher"
    description = "抓取最新科技新闻（来源：V2EX），并整理成摘要。"
    args_schema = NewsFetcherArgs
    
    permissions = {
        "network": True,
        "filesystem": False, # 注意：这里设为 False，因为脚本在 Docker 内运行，不需要挂载宿主机文件
        "max_cpu": 0.3,
        "max_memory": 128
    }

    def __init__(self):
        super().__init__()
        self.sandbox = get_sandbox()
        # 获取当前脚本所在的目录
        self.skill_dir = os.path.dirname(os.path.abspath(__file__))

    def execute(self, count: int = 5) -> str:
        try:
            # 1. 读取脚本文件内容
            script_path = os.path.join(self.skill_dir, "scripts", "fetch_script.py")
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            # 2. 构建执行命令（将 count 作为参数传入）
            # 注意：因为 Docker 沙箱是隔离的，我们不能直接用文件路径
            # 所以这里还是要把脚本内容传进去，但至少我们的代码干净了
            
            python_code = f"""
import sys
sys.argv = ['fetch_script', '{count}']

{script_content}
"""
            
            # 3. 调用沙箱执行
            result = self.sandbox.execute_code(
                code=python_code,
                permissions=self.permissions
            )
            
            return f"📰 最新 V2EX 热点：\n{result}"
            
        except Exception as e:
            return f"❌ 新闻抓取失败: {str(e)}"