import os
import json
import glob
import uuid
import random
import subprocess
import threading
import datetime
import time
import logging
from src.skills.base import BaseSkill

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")
ROLES_DIR = os.path.join(WORKSPACE_DIR, "audios", "roles")

GRADIO_SERVICE_URL = "http://127.0.0.1:7860/"


class TextToAudioSkill(BaseSkill):
    name = "text_to_audio"
    description = (
        "根据脚本JSON批量将文本转为语音，调用本地 IndexTTS 服务进行音色克隆。"
        "扫描workspace目录下最新的video-script-*.json，遍历captions生成MP3，"
        "并更新JSON中的audio和audio_length字段。"
    )

    permissions = {
        "network": True,
        "filesystem": True,
        "max_cpu": 0.5,
        "max_memory": 512,
    }

    def execute(self, **kwargs) -> str:
        running_status = self._get_running_status()
        if running_status:
            return running_status

        if not self._is_service_available():
            return "⚠️ 本地语音合成服务未启用！请先启动 IndexTTS 服务（http://127.0.0.1:7860）。"

        pattern = os.path.join(WORKSPACE_DIR, "video-script-*.json")
        json_files = glob.glob(pattern)
        if not json_files:
            return f"❌ 在 {WORKSPACE_DIR} 中未找到 video-script-*.json 文件。"

        latest_file = max(json_files, key=os.path.getmtime)
        logger.info("Latest script file: %s", latest_file)

        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return f"❌ 读取 JSON 文件失败: {str(e)}"

        project_id = data.get("meta", {}).get("project_id", "")
        if not project_id:
            project_id = uuid.uuid4().hex
            data.setdefault("meta", {})["project_id"] = project_id
            try:
                with open(latest_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except IOError as e:
                return f"❌ 写入 project_id 失败: {str(e)}"

        audios_dir = os.path.join(WORKSPACE_DIR, project_id, "audios")
        os.makedirs(audios_dir, exist_ok=True)

        script = data.get("script", [])
        if not script:
            return "❌ JSON 文件中没有 script 数据。"

        role_audio_map = self._build_role_audio_map(data)
        if not role_audio_map:
            return (
                f"❌ 未找到参考音频。请在 {ROLES_DIR} 中放入参考音频文件。\n"
                f"需要的文件：旁白.mp3, 男1.mp3, 男2.mp3, 男3.mp3, 女1.mp3, 女2.mp3, 女3.mp3, default.mp3"
            )

        logger.info("Role -> Audio mapping: %s", {k: os.path.basename(v) for k, v in role_audio_map.items()})

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        jobs = []
        caption_refs = []
        global_seq = 0

        for scene in script:
            for caption in scene.get("captions", []):
                srt_text = caption.get("srt", "").strip()
                if not srt_text:
                    continue

                role = caption.get("role", "未知")
                ref_audio = role_audio_map.get(role)
                if not ref_audio or not os.path.isfile(ref_audio):
                    continue

                seq_str = f"{global_seq:03d}"
                audio_filename = f"audio-{role}-{seq_str}-{timestamp}.mp3"
                audio_path = os.path.join(audios_dir, audio_filename)

                jobs.append({
                    "ref_audio": ref_audio,
                    "text": srt_text,
                    "output": audio_path,
                })
                caption_refs.append((caption, audio_filename, audio_path, role, seq_str))
                global_seq += 1

        if not jobs:
            return "❌ 没有可生成语音的文本（所有 srt 为空或参考音频缺失）。"

        status_path = os.path.join(audios_dir, f"_status_{timestamp}.json")
        self._write_status(status_path, "running", 0, len(jobs), "正在启动后台合成...")

        thread = threading.Thread(
            target=self._run_background,
            args=(jobs, caption_refs, status_path, latest_file, data, timestamp, audios_dir),
            daemon=True,
        )
        thread.start()

        role_summary = ", ".join(
            f"{role}={os.path.basename(audio)}"
            for role, audio in role_audio_map.items()
        )
        return (
            f"🎙️ 已启动后台语音合成，共 {len(jobs)} 条任务\n"
            f"角色音色: {role_summary}\n"
            f"状态文件: {os.path.basename(status_path)}\n"
            f"完成后会自动更新 JSON，届时可查看结果。"
        )

    def _run_background(self, jobs, caption_refs, status_path, json_path, data, timestamp, audios_dir):
        from gradio_client import Client, handle_file

        total = len(jobs)
        generated = 0

        try:
            client = Client(GRADIO_SERVICE_URL)
        except Exception as e:
            self._write_status(status_path, "error", 0, total, f"无法连接服务: {e}")
            self._notify_user(0, total, error=f"无法连接服务: {e}")
            return

        for idx, job in enumerate(jobs):
            ref_audio = job["ref_audio"]
            text = job["text"]
            output_path = job["output"]

            caption, audio_filename, audio_path, role, seq_str = caption_refs[idx]

            self._write_status(status_path, "running", generated, total,
                               f"正在合成 [{idx+1}/{total}]: [{seq_str}] {role}")

            try:
                result = client.predict(
                    prompt=handle_file(ref_audio),
                    text=text,
                    infer_mode="批次推理",
                    max_text_tokens_per_sentence=120,
                    sentences_bucket_max_size=8,
                    param_5=True,
                    param_6=0.8,
                    param_7=30,
                    param_8=1.0,
                    param_9=0.0,
                    param_10=1,
                    param_11=10.0,
                    param_12=600,
                    api_name="/gen_single",
                )

                wav_path = result.get("value", "") if isinstance(result, dict) else str(result)
                if not wav_path or not os.path.isfile(wav_path):
                    self._write_status(status_path, "running", generated, total,
                                       f"跳过 [{idx+1}/{total}]: [{seq_str}] {role} - 服务返回空")
                    continue

                duration = self._get_wav_duration(wav_path)

                try:
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-i", wav_path,
                        "-codec:a", "libmp3lame", "-b:a", "192k",
                        output_path,
                    ]
                    subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
                except Exception as e:
                    logger.warning("ffmpeg convert failed for %s: %s", output_path, e)
                    try:
                        os.remove(wav_path)
                    except OSError:
                        pass
                    continue

                try:
                    os.remove(wav_path)
                except OSError:
                    pass

                audio_length_str = self._format_duration(duration)
                caption["audio"] = audio_filename
                caption["audio_length"] = audio_length_str
                generated += 1

                self._write_status(status_path, "running", generated, total,
                                   f"已完成 {generated}/{total}，当前: [{seq_str}] {role}")

            except Exception as e:
                logger.error("TTS failed for [%s] %s: %s", seq_str, role, e)
                self._write_status(status_path, "running", generated, total,
                                   f"出错 [{idx+1}/{total}]: [{seq_str}] {role} - {str(e)[:60]}")

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

        self._write_status(status_path, "done", generated, total,
                           f"全部完成！JSON 已更新: {os.path.basename(json_path)}")
        self._notify_user(generated, total)

    @staticmethod
    def _is_service_available() -> bool:
        try:
            import requests
            r = requests.get(f"{GRADIO_SERVICE_URL}gradio_api/info", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

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
            msg = f"[Mason] 语音合成出错: {error[:100]}"
        else:
            msg = f"[Mason] 语音合成全部完成！{done}/{total}"

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
        pattern = os.path.join(WORKSPACE_DIR, "*", "audios", "_status_*.json")
        files = glob.glob(pattern)
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
                f"🎙️ 语音合成进行中：{done}/{total} ({pct})\n"
                f"状态: {message}"
            )

        if state == "done":
            return (
                f"✅ 语音合成已完成：{done}/{total}\n"
                f"{message}"
            )

        if state == "error":
            return (
                f"❌ 语音合成出错：{done}/{total}\n"
                f"{message}"
            )

        return ""

    def _build_role_audio_map(self, data: dict) -> dict:
        meta_roles = data.get("meta", {}).get("roles", [])

        role_genders = {}
        for role_def in meta_roles:
            parts = role_def.split()
            role_name = parts[0]
            gender = parts[1] if len(parts) > 1 else None
            role_genders[role_name] = gender

        all_roles = set()
        for scene in data.get("script", []):
            for caption in scene.get("captions", []):
                role = caption.get("role", "")
                if role:
                    all_roles.add(role)

        male_pool = []
        female_pool = []
        if os.path.isdir(ROLES_DIR):
            for f in sorted(os.listdir(ROLES_DIR)):
                if not f.endswith(".mp3"):
                    continue
                if f.startswith("男"):
                    male_pool.append(f)
                elif f.startswith("女"):
                    female_pool.append(f)

        used_male = {}
        used_female = {}
        role_map = {}

        for role in all_roles:
            if role == "旁白":
                path = os.path.join(ROLES_DIR, "旁白.mp3")
                role_map[role] = path if os.path.isfile(path) else os.path.join(ROLES_DIR, "default.mp3")
                continue

            gender = role_genders.get(role)

            if gender == "男" and male_pool:
                if role not in used_male:
                    used_male[role] = random.choice(male_pool)
                role_map[role] = os.path.join(ROLES_DIR, used_male[role])
            elif gender == "女" and female_pool:
                if role not in used_female:
                    used_female[role] = random.choice(female_pool)
                role_map[role] = os.path.join(ROLES_DIR, used_female[role])
            else:
                role_map[role] = os.path.join(ROLES_DIR, "default.mp3")

        return role_map

    @staticmethod
    def _get_wav_duration(wav_path: str) -> float:
        try:
            import wave
            with wave.open(wav_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return frames / rate
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_us = int(seconds * 1_000_000)
        secs = total_us // 1_000_000
        micros = total_us % 1_000_000
        return f"{secs},{micros:06d}"


def create_skill():
    return TextToAudioSkill()