# install_skill.py
import os
import sys
import shutil
import yaml
import tempfile
import urllib.request
import zipfile

# 强制使用 UTF-8 编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(ROOT_DIR, "src", "skills", "builtin")

def install_skill(source_path):
    """安装 Skill（支持本地目录和网络 ZIP）"""
    print("[INFO] Installing skill from: {}".format(source_path))
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print("[INFO] Temp directory: {}".format(temp_dir))
    
    try:
        # 判断来源类型
        if source_path.startswith(("http://", "https://")):
            # 1. 网络 ZIP 文件
            print("[INFO] Downloading from web...")
            temp_zip = os.path.join(temp_dir, "skill.zip")
            
            try:
                urllib.request.urlretrieve(source_path, temp_zip)
            except Exception as e:
                print("[ERROR] Download failed: {}".format(e))
                return False
            
            # 解压 ZIP
            print("[INFO] Extracting ZIP...")
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            skill_source_dir = extract_dir
            
        elif source_path.startswith("file:///"):
            # 2. 本地 file:// 协议（目录）
            print("[INFO] Using local file:// protocol...")
            local_path = source_path[8:]  # 去掉 "file:///"
            if local_path.startswith("/"):
                local_path = local_path[1:]  # 去掉开头的斜杠
            
            if not os.path.exists(local_path):
                print("[ERROR] Local path not found: {}".format(local_path))
                return False
            
            skill_source_dir = local_path
            
        elif os.path.exists(source_path):
            # 3. 直接是本地路径（目录）
            print("[INFO] Using local directory...")
            skill_source_dir = source_path
            
        else:
            print("[ERROR] Invalid source: {}".format(source_path))
            return False
        
        # 验证 skill.yaml 是否存在
        skill_yaml_path = os.path.join(skill_source_dir, "skill.yaml")
        if not os.path.exists(skill_yaml_path):
            print("[ERROR] skill.yaml not found in: {}".format(skill_source_dir))
            return False
        
        # 读取 skill.yaml
        with open(skill_yaml_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)
        
        skill_name = manifest.get("name")
        if not skill_name:
            print("[ERROR] 'name' field missing in skill.yaml")
            return False
        
        # 目标目录
        target_dir = os.path.join(SKILLS_DIR, skill_name)
        
        # 备份旧版本
        if os.path.exists(target_dir):
            backup_dir = "{}_backup_{}".format(target_dir, int(os.time.time()))
            print("[INFO] Backing up to: {}".format(backup_dir))
            shutil.move(target_dir, backup_dir)
        
        # 复制新版本
        print("[INFO] Copying to: {}".format(target_dir))
        shutil.copytree(skill_source_dir, target_dir)
        
        print("[SUCCESS] Successfully installed: {}".format(skill_name))
        print("[INFO] Please restart Mason to activate the new skill.")
        return True
        
    except Exception as e:
        print("[ERROR] Installation failed: {}".format(e))
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python install_skill.py <source_path>")
        print("Examples:")
        print("  python install_skill.py https://github.com/user/weather-skill/archive/main.zip")
        print("  python install_skill.py file:///D:/WorkSpace/Coding/weather_skill")
        print("  python install_skill.py D:/WorkSpace/Coding/weather_skill")
        sys.exit(1)
    
    import time
    source_path = sys.argv[1]
    if not install_skill(source_path):
        sys.exit(1)