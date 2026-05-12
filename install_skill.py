# install_skill.py
import os
import sys
import shutil
import tempfile
import yaml
import subprocess
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = ROOT_DIR / "src" / "skills" / "builtin"
TEMPLATE_PATH = ROOT_DIR / "src" / "skills" / "skill_template.yaml"

def run_cmd(command: str, cwd: Path = None):
    """运行 shell 命令"""
    print(f"🔧 Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def install_skill(repo_url: str):
    """安装 Skill"""
    print(f"📦 Installing skill from: {repo_url}")
    
    # 1. 克隆仓库到临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        run_cmd(f"git clone {repo_url} skill_repo", cwd=tmp_path)
        
        repo_path = tmp_path / "skill_repo"
        
        # 2. 验证 skill.yaml
        manifest_path = repo_path / "skill.yaml"
        if not manifest_path.exists():
            print("❌ skill.yaml not found. Aborting.")
            sys.exit(1)
            
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
        
        skill_name = manifest.get("name")
        if not skill_name:
            print("❌ 'name' missing in skill.yaml.")
            sys.exit(1)
            
        print(f"✅ Found skill: {manifest.get('display_name', skill_name)}")
        
        # 3. 检查是否已安装
        target_dir = SKILLS_DIR / skill_name
        if target_dir.exists():
            print(f"❌ Skill '{skill_name}' already exists.")
            sys.exit(1)
            
        # 4. 移动文件到 builtin 目录
        shutil.copytree(repo_path, target_dir)
        print(f"✅ Copied files to {target_dir}")
        
        # 5. 处理依赖（更新 requirements.txt）
        requirements = manifest.get("requirements", [])
        if requirements:
            req_file = ROOT_DIR / "requirements.txt"
            with open(req_file, 'a') as f:
                f.write("\n# Auto-installed by skill: " + skill_name + "\n")
                for req in requirements:
                    f.write(req + "\n")
            print(f"✅ Added {len(requirements)} dependencies to requirements.txt")
            print("⚠️ Please run 'pip install -r requirements.txt' to install them.")
        
        # 6. 提示重启
        print(f"\n🎉 Skill '{skill_name}' installed successfully!")
        print(f"🔄 Please restart Mason to activate the skill.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python install_skill.py <github_repo_url>")
        sys.exit(1)
    
    repo_url = sys.argv[1]
    install_skill(repo_url)