# install_skill.py
import os
import sys
import shutil
import yaml
import time
import tempfile
import urllib.request
import zipfile

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(ROOT_DIR, "src", "skills", "user")


def install_skill(source_path):
    print("[INFO] Installing skill from: {}".format(source_path))

    temp_dir = tempfile.mkdtemp()
    print("[INFO] Temp directory: {}".format(temp_dir))

    try:
        if source_path.startswith(("http://", "https://")):
            print("[INFO] Downloading from web...")
            temp_zip = os.path.join(temp_dir, "skill.zip")

            try:
                urllib.request.urlretrieve(source_path, temp_zip)
            except Exception as e:
                print("[ERROR] Download failed: {}".format(e))
                return False

            print("[INFO] Extracting ZIP...")
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            skill_source_dir = extract_dir

        elif source_path.startswith("file:///"):
            print("[INFO] Using local file:// protocol...")
            local_path = source_path[8:]
            if local_path.startswith("/"):
                local_path = local_path[1:]

            if not os.path.exists(local_path):
                print("[ERROR] Local path not found: {}".format(local_path))
                return False

            skill_source_dir = local_path

        elif os.path.exists(source_path):
            print("[INFO] Using local directory...")
            skill_source_dir = source_path

        else:
            print("[ERROR] Invalid source: {}".format(source_path))
            return False

        skill_yaml_path = os.path.join(skill_source_dir, "skill.yaml")
        if not os.path.exists(skill_yaml_path):
            print("[ERROR] skill.yaml not found in: {}".format(skill_source_dir))
            return False

        with open(skill_yaml_path, 'r', encoding='utf-8') as f:
            manifest = yaml.safe_load(f)

        skill_name = manifest.get("name")
        if not skill_name:
            print("[ERROR] 'name' field missing in skill.yaml")
            return False

        target_dir = os.path.join(SKILLS_DIR, skill_name)

        if os.path.exists(target_dir):
            backup_dir = "{}_backup_{}".format(target_dir, int(time.time()))
            print("[INFO] Backing up to: {}".format(backup_dir))
            shutil.move(target_dir, backup_dir)

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
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python install_skill.py <source_path>")
        print("Examples:")
        print("  python install_skill.py https://github.com/user/weather-skill/archive/main.zip")
        print("  python install_skill.py file:///D:/WorkSpace/Coding/weather_skill")
        print("  python install_skill.py D:/WorkSpace/Coding/weather_skill")
        sys.exit(1)

    source_path = sys.argv[1]
    if not install_skill(source_path):
        sys.exit(1)