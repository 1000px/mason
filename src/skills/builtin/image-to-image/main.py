import os
import json
import glob
import subprocess
import threading
import datetime
import logging
import requests
from openai import OpenAI
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")


class ImageToImageArgs(BaseModel):
    pass


class ImageToImageSkill(BaseSkill):
    name = "image_to_image"
    description = "根据脚本批量图生图。读取 video-script JSON 中的 image_prompt，用即梦 Seedream 模型逐条生成场景图片。"
    args_schema = ImageToImageArgs

    permissions = {
        "network": True,
        "filesystem": True,
        "max_cpu": 0.3,
        "max_memory": 512,
    }

    def execute(self) -> str:
        running_status = self._get_running_status()
        if running_status:
            return running_status

        script_path = self._find_latest_script()
        if not script_path:
            return "❌ 未找到 video-script-*.json 文件，请先生成视频脚本。"

        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)

        project_id = script_data.get("meta", {}).get("project_id", "")
        if not project_id:
            return "❌ 脚本中未找到 project_id。"

        script_items = script_data.get("script", [])
        items_with_prompt = [
            (i, item) for i, item in enumerate(script_items)
            if item.get("image_prompt", "").strip()
        ]

        if not items_with_prompt:
            return "❌ 脚本中没有 image_prompt 字段，无需生成图片。"

        resources_dir = os.path.join(WORKSPACE_DIR, project_id, "resources")
        os.makedirs(resources_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        status_path = os.path.join(resources_dir, f"_img_gen_status_{timestamp}.json")
        self._write_status(status_path, "running", 0, len(items_with_prompt), "正在准备...")

        thread = threading.Thread(
            target=self._run_background,
            args=(script_path, script_data, project_id, items_with_prompt, resources_dir, status_path),
            daemon=True,
        )
        thread.start()

        return (
            f"🎨 图片批量生成任务已启动（{len(items_with_prompt)} 张），后台运行中...\n"
            f"随时问我\"图片生成进度\"查看状态。"
        )

    def _run_background(self, script_path, script_data, project_id, items_with_prompt, resources_dir, status_path):
        total = len(items_with_prompt)

        api_key = os.getenv("JIMENG_API_KEY", "")
        if not api_key:
            self._write_status(status_path, "error", 0, total, "未配置 JIMENG_API_KEY")
            self._notify_user(0, total, error="未配置 JIMENG_API_KEY")
            return

        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )

        results = []
        script_list = script_data["script"]

        for idx, (script_idx, item) in enumerate(items_with_prompt):
            image_prompt = item["image_prompt"].strip()

            self._write_status(status_path, "running", idx, total,
                               f"正在生成第 {idx + 1}/{total} 张图片...")

            logger.info("[%d/%d] Generating: %s...", idx + 1, total, image_prompt[:60])

            try:
                response = client.images.generate(
                    model="doubao-seedream-4-0-250828",
                    prompt=image_prompt,
                    size="2560x1440",
                    response_format="url",
                    extra_body={
                        "watermark": False,
                    },
                )

                image_url = response.data[0].url
                image_name = f"image_{script_idx:03d}.jpg"
                image_path = os.path.join(resources_dir, image_name)

                resp = requests.get(image_url, timeout=60)
                resp.raise_for_status()
                with open(image_path, "wb") as f:
                    f.write(resp.content)

                script_list[script_idx]["image_name"] = image_name
                results.append(f"✅ 第 {idx + 1} 张: {image_name}")

                self._write_status(status_path, "running", idx + 1, total,
                                   f"已完成 {idx + 1}/{total}: {image_name}")

            except Exception as e:
                results.append(f"❌ 第 {idx + 1} 张失败: {str(e)[:80]}")
                self._write_status(status_path, "running", idx + 1, total,
                                   f"第 {idx + 1} 张失败 ({idx + 1}/{total})")

        try:
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            self._write_status(status_path, "error", total, total, f"写入脚本失败: {e}")
            return

        summary = f"📝 图片生成完成（{total} 张）：\n\n" + "\n".join(results)
        self._write_status(status_path, "done", total, total, summary)
        self._notify_user(total, total)

    @staticmethod
    def _find_latest_script():
        pattern = os.path.join(WORKSPACE_DIR, "video-script-*.json")
        files = glob.glob(pattern)
        if not files:
            return ""
        return max(files, key=os.path.getmtime)

    @staticmethod
    def _write_status(status_path, state, done, total, message):
        try:
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump({
                    "state": state,
                    "done": done,
                    "total": total,
                    "message": message,
                }, f, ensure_ascii=False)
        except IOError:
            pass

    @staticmethod
    def _notify_user(done, total, error=None):
        if error:
            msg = f"[Mason] 图片生成出错: {error[:100]}"
        else:
            msg = f"[Mason] 图片生成全部完成！{done}/{total}"

        print()
        print("=" * 50)
        print(msg)
        print("=" * 50)
        print()

        try:
            ps_cmd = (
                'Add-Type -AssemblyName System.Windows.Forms; '
                f'$n = New-Object System.Windows.Forms.NotifyIcon; '
                '$n.Icon = [System.Drawing.SystemIcons]::Information; '
                f'$n.BalloonTipTitle = "Mason"; '
                f'$n.BalloonTipText = "{msg}"; '
                '$n.Visible = $true; '
                '$n.ShowBalloonTip(10000); '
                'Start-Sleep -Seconds 12; '
                '$n.Dispose()'
            )
            subprocess.Popen(
                ['powershell', '-Command', ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    @staticmethod
    def _get_running_status() -> str:
        patterns = [
            os.path.join(WORKSPACE_DIR, "*", "resources", "_img_gen_status_*.json"),
        ]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        if not files:
            return ""

        latest = max(files, key=os.path.getmtime)
        try:
            with open(latest, "r", encoding="utf-8") as f:
                s = json.load(f)
        except (json.JSONDecodeError, IOError):
            return ""

        state = s.get("state", "")
        done = s.get("done", 0)
        total = s.get("total", 0)
        message = s.get("message", "")

        if state == "running":
            pct = f"{done / total * 100:.0f}%" if total > 0 else "0%"
            return (
                f"🎨 图片生成进行中：{done}/{total} ({pct})\n"
                f"状态: {message}"
            )

        if state == "done":
            return message

        if state == "error":
            return (
                f"❌ 图片生成出错：{done}/{total}\n"
                f"{message}"
            )

        return ""