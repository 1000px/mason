import os
import json
import glob
import subprocess
import threading
import datetime
import logging
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field

try:
    from opencc import OpenCC
    _opencc = OpenCC('t2s')
except ImportError:
    _opencc = None

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")
LEGACY_AUDIOS_DIR = os.path.join(WORKSPACE_DIR, "audios")
MODEL_DIR = os.path.join(PROJECT_ROOT, "src", "third_party", "faster-whisper-base")

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma", ".aac", ".opus"}


class AudioToSrtArgs(BaseModel):
    audio_file: str = Field(
        default="",
        description="要处理的音频文件名（不含路径），例如 'lecture.mp3'。留空则处理 audios 目录下所有支持的音频文件。",
    )
    language: str = Field(
        default="zh",
        description="音频语言代码，例如 'zh'（中文）、'en'（英文）、'ja'（日文）。默认 'zh'。",
    )
    project_id: str = Field(
        default="",
        description="项目 ID，用于定位 workspace/{project_id}/audios/ 目录。留空则使用旧版 workspace/audios/ 目录。",
    )
    max_chars: int = Field(
        default=20,
        description="每条字幕的最大字数，超出则按词级时间戳拆分。设为 0 表示不限制。默认 20。",
    )


class AudioToSrtSkill(BaseSkill):
    name = "audio_to_srt"
    description = "将 audios 目录中的音频文件转录为 SRT 字幕文件，使用本地 faster-whisper-base 模型。"
    args_schema = AudioToSrtArgs

    permissions = {
        "network": False,
        "filesystem": True,
        "max_cpu": 0.8,
        "max_memory": 2048,
    }

    def execute(self, audio_file: str = "", language: str = "zh", project_id: str = "", max_chars: int = 20) -> str:
        running_status = self._get_running_status()
        if running_status:
            return running_status

        if not os.path.isdir(MODEL_DIR):
            return f"❌ 模型路径不存在: {MODEL_DIR}"

        if not project_id:
            project_id = self._detect_project_id()

        if project_id:
            audios_dir = os.path.join(WORKSPACE_DIR, project_id, "audios")
        else:
            audios_dir = LEGACY_AUDIOS_DIR

        if not os.path.isdir(audios_dir):
            os.makedirs(audios_dir, exist_ok=True)
            return f"📁 audios 目录已创建（{audios_dir}），请放入音频文件后再试。"

        if audio_file:
            target_path = os.path.join(audios_dir, audio_file)
            if not os.path.isfile(target_path):
                return f"❌ 音频文件不存在: {target_path}"
            ext = os.path.splitext(audio_file)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                return f"❌ 不支持的音频格式: {ext}。支持的格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            audio_paths = [target_path]
        else:
            audio_paths = []
            for f in sorted(os.listdir(audios_dir)):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    audio_paths.append(os.path.join(audios_dir, f))

            if not audio_paths:
                return f"📁 audios 目录中没有支持的音频文件。\n支持的格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}\n目录: {audios_dir}"

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        status_path = os.path.join(audios_dir, f"_srt_status_{timestamp}.json")
        self._write_status(status_path, "running", 0, len(audio_paths), "正在加载模型...")

        thread = threading.Thread(
            target=self._run_background,
            args=(audio_paths, language, status_path, timestamp, audios_dir, max_chars),
            daemon=True,
        )
        thread.start()

        return (
            f"🎙️ 字幕生成任务已启动（{len(audio_paths)} 个文件），后台运行中...\n"
            f"随时问我\"字幕生成进度\"查看状态。"
        )

    def _run_background(self, audio_paths, language, status_path, timestamp, audios_dir, max_chars):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            self._write_status(status_path, "error", 0, len(audio_paths), "缺少 faster-whisper 依赖")
            self._notify_user(0, len(audio_paths), error="缺少 faster-whisper 依赖")
            return

        logger.info("Loading model from %s (device=cpu, compute_type=int8)...", MODEL_DIR)
        try:
            model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8")
        except Exception as e:
            self._write_status(status_path, "error", 0, len(audio_paths), f"加载模型失败: {e}")
            self._notify_user(0, len(audio_paths), error=f"加载模型失败: {e}")
            return

        total = len(audio_paths)
        results = []

        for idx, audio_path in enumerate(audio_paths):
            audio_name = os.path.basename(audio_path)
            base_name = os.path.splitext(audio_name)[0]
            srt_path = os.path.join(audios_dir, f"{base_name}-sub.srt")

            self._write_status(status_path, "running", idx, total,
                               f"正在转录: {audio_name} ({idx + 1}/{total})")

            logger.info("[%d/%d] Transcribing: %s", idx + 1, total, audio_name)

            try:
                segments, info = model.transcribe(audio_path, beam_size=5, language=language, word_timestamps=True)
            except Exception as e:
                results.append(f"❌ {audio_name}: 转录失败 - {str(e)}")
                self._write_status(status_path, "running", idx + 1, total,
                                   f"{audio_name} 转录失败 ({idx + 1}/{total})")
                continue

            detected_lang = info.language
            confidence = info.language_probability

            try:
                with open(srt_path, "w", encoding="utf-8") as f:
                    seg_count = 0
                    for segment in segments:
                        for start, end, text in self._split_segment(segment, max_chars):
                            seg_count += 1
                            f.write(f"{seg_count}\n{self._format_timestamp(start)} --> {self._format_timestamp(end)}\n{text}\n\n")
            except IOError as e:
                results.append(f"❌ {audio_name}: 写入字幕文件失败 - {str(e)}")
                self._write_status(status_path, "running", idx + 1, total,
                                   f"{audio_name} 写入失败 ({idx + 1}/{total})")
                continue

            results.append(
                f"✅ {audio_name} → {base_name}-sub.srt "
                f"（{seg_count} 条字幕, 语言: {detected_lang}, 置信度: {confidence:.0%}）"
            )
            self._write_status(status_path, "running", idx + 1, total,
                               f"已完成: {audio_name} ({idx + 1}/{total})")

        summary = f"📝 字幕生成完成（{total} 个文件）：\n\n" + "\n".join(results)
        self._write_status(status_path, "done", total, total, summary)
        self._notify_user(total, total)

    @staticmethod
    def _split_segment(segment, max_chars):
        text = segment.text.strip()
        if _opencc is not None:
            text = _opencc.convert(text)

        if max_chars <= 0 or not segment.words or len(text) <= max_chars:
            yield segment.start, segment.end, text
            return

        words = segment.words
        batch = []
        char_count = 0

        for word in words:
            batch.append(word)
            char_count += len(word.word)
            if char_count >= max_chars:
                sub_text = ''.join(w.word for w in batch).strip()
                if _opencc is not None:
                    sub_text = _opencc.convert(sub_text)
                if sub_text:
                    yield batch[0].start, batch[-1].end, sub_text
                batch = []
                char_count = 0

        if batch:
            sub_text = ''.join(w.word for w in batch).strip()
            if _opencc is not None:
                sub_text = _opencc.convert(sub_text)
            if sub_text:
                yield batch[0].start, batch[-1].end, sub_text

    @staticmethod
    def _detect_project_id() -> str:
        pattern = os.path.join(WORKSPACE_DIR, "video-script-*.json")
        json_files = glob.glob(pattern)
        if not json_files:
            return ""

        latest_file = max(json_files, key=os.path.getmtime)
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("meta", {}).get("project_id", "")
        except (json.JSONDecodeError, IOError):
            return ""

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
            msg = f"[Mason] 字幕生成出错: {error[:100]}"
        else:
            msg = f"[Mason] 字幕生成全部完成！{done}/{total}"

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
            os.path.join(WORKSPACE_DIR, "*", "audios", "_srt_status_*.json"),
            os.path.join(LEGACY_AUDIOS_DIR, "_srt_status_*.json"),
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
                f"🎙️ 字幕生成进行中：{done}/{total} ({pct})\n"
                f"状态: {message}"
            )

        if state == "done":
            return message

        if state == "error":
            return (
                f"❌ 字幕生成出错：{done}/{total}\n"
                f"{message}"
            )

        return ""

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        dt = datetime.timedelta(seconds=seconds)
        hours, remainder = divmod(dt.seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        milliseconds = dt.microseconds // 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def create_skill():
    return AudioToSrtSkill()