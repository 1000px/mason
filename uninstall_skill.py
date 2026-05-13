# uninstall_skill.py
import os
import sys
import shutil
import yaml
import stat
from pathlib import Path

# 强制使用 UTF-8 编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent
BUILTIN_SKILLS_DIR = ROOT_DIR / "src" / "skills" / "builtin"
USER_SKILLS_DIR = ROOT_DIR / "src" / "skills" / "user"
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"

# 定义系统核心引导文件
CORE_SYSTEM_FILES = [
    ROOT_DIR / "src" / "main.py",
    ROOT_DIR / "src" / "agent.py", 
    ROOT_DIR / "src" / "graph" / "__init__.py",
    ROOT_DIR / "src" / "tools" / "__init__.py"
]

def handle_remove_readonly(func, path, exc):
    """Windows 专用：处理只读文件删除失败的情况"""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def force_remove_directory(path: Path):
    """强制删除目录，处理 Windows 权限问题"""
    if not path.exists():
        return
    
    print(f"[INFO] Force removing directory: {path}")
    
    try:
        # 方法1：使用 shutil.rmtree 带错误处理
        shutil.rmtree(path, onerror=handle_remove_readonly)
        print(f"[SUCCESS] Successfully deleted: {path}")
    except Exception as e:
        print(f"[WARNING] Standard removal failed: {e}")
        
        # 方法2：尝试使用系统命令
        try:
            print(f"[INFO] Trying system command...")
            # Windows 命令：强制删除目录及其所有内容
            os.system(f'rmdir /s /q "{path}"')
            if not path.exists():
                print(f"[SUCCESS] Successfully deleted with system command")
                return
        except:
            pass
        
        # 方法3：逐个文件删除（最暴力的方法）
        try:
            print(f"[INFO] Trying manual deletion...")
            for root, dirs, files in os.walk(path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.chmod(file_path, stat.S_IWRITE)
                        os.remove(file_path)
                    except:
                        pass
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        os.rmdir(dir_path)
                    except:
                        pass
            os.rmdir(path)
            print(f"[SUCCESS] Successfully deleted manually")
        except Exception as e2:
            print(f"[ERROR] All deletion methods failed: {e2}")
            raise

def is_system_skill(skill_name: str) -> bool:
    """动态检查：该 skill 是否是系统正常运行所必须的"""
    for core_file in CORE_SYSTEM_FILES:
        if core_file.exists():
            try:
                content = core_file.read_text(encoding='utf-8')
                if f"'{skill_name}'" in content or f'"{skill_name}"' in content:
                    return True
            except Exception:
                continue
    return False

def remove_skill_dependencies(skill_name: str):
    """从 requirements.txt 中移除该 Skill 的依赖标记"""
    if not REQUIREMENTS_FILE.exists():
        return
    
    with open(REQUIREMENTS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    skip_mode = False
    removed = False
    
    for line in lines:
        if f"# Auto-installed by skill: {skill_name}" in line:
            skip_mode = True
            removed = True
            continue
        
        if skip_mode and (line.strip() == "" or line.startswith("#")):
            skip_mode = False
        
        if not skip_mode:
            new_lines.append(line)
    
    if removed:
        with open(REQUIREMENTS_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"[INFO] Removed dependencies for skill '{skill_name}' from requirements.txt")

def uninstall_skill(skill_name: str):
    print(f"[INFO] Uninstalling skill: {skill_name}")

    if is_system_skill(skill_name):
        print(f"[ERROR] Cannot uninstall system skill: {skill_name}")
        print("   This skill is required for Mason's core functionality.")
        sys.exit(1)

    skill_dir = None
    for base_dir in (USER_SKILLS_DIR, BUILTIN_SKILLS_DIR):
        candidate = base_dir / skill_name
        if candidate.exists():
            skill_dir = candidate
            break

    if skill_dir is None:
        print(f"[ERROR] Skill '{skill_name}' not found.")
        sys.exit(1)
    
    # 3. 读取 skill.yaml 获取依赖信息
    manifest_path = skill_dir / "skill.yaml"
    dependencies = []
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
            dependencies = manifest.get("requirements", [])
    
    # 4. 强制删除 Skill 目录
    try:
        force_remove_directory(skill_dir)
    except Exception as e:
        print(f"[ERROR] Failed to delete directory: {e}")
        print(f"[TIP] Try closing any programs that might be using files in this directory.")
        print(f"   Or manually delete the folder: {skill_dir}")
        sys.exit(1)
    
    # 5. 移除依赖标记
    remove_skill_dependencies(skill_name)
    
    # 6. 提示用户
    print(f"\n[SUCCESS] Skill '{skill_name}' has been uninstalled successfully!")
    if dependencies:
        print(f"[INFO] Note: The following dependencies were used by this skill:")
        for dep in dependencies:
            print(f"   - {dep}")
        print("   You may want to manually remove them if they are no longer needed.")
    
    print(f"\n[INFO] Please restart Mason to apply changes.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python uninstall_skill.py <skill_name>")
        print("Example: python uninstall_skill.py weather")
        sys.exit(1)
    
    skill_name = sys.argv[1]
    uninstall_skill(skill_name)