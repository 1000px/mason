import os
import glob
import json
import re
import difflib
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")


class FixSrtArgs(BaseModel):
    project_id: str = Field(
        default="",
        description="项目ID，留空则自动从最新的 video-script-*.json 中检测",
    )


class FixSrtSkill(BaseSkill):
    name = "fix_srt"
    description = "修正 SRT 字幕文件中的错别字。基于 video-script-*.json 中的正确文本，校正 Whisper 转录产生的错别字，保留原有时间戳。"
    args_schema = FixSrtArgs

    permissions = {
        "network": False,
        "filesystem": True,
        "max_cpu": 0.3,
        "max_memory": 256,
    }

    def execute(self, project_id: str = "") -> str:
        if not project_id:
            project_id = FixSrtSkill._detect_project_id()

        if not project_id:
            return "❌ 未找到 video-script-*.json，请先生成视频脚本。"

        audios_dir = os.path.join(WORKSPACE_DIR, project_id, "audios")
        if not os.path.isdir(audios_dir):
            return f"❌ audios 目录不存在: {audios_dir}"

        srt_files = sorted(glob.glob(os.path.join(audios_dir, "*-sub.srt")))
        if not srt_files:
            return f"❌ audios 目录中没有找到 -sub.srt 文件，请先生成字幕。"

        video_script = self._load_video_script(project_id)
        if not video_script:
            return "❌ 无法读取 video-script-*.json。"

        caption_map = self._build_caption_map(video_script)

        total = len(srt_files)
        fixed = 0
        unchanged = 0
        errors = 0
        total_changes = 0

        for srt_path in srt_files:
            basename = os.path.basename(srt_path)
            audio_name = basename.replace("-sub.srt", ".mp3")

            correct_srt = caption_map.get(audio_name, "")
            if not correct_srt:
                unchanged += 1
                continue

            try:
                changes = self._fix_one_srt(srt_path, correct_srt)
                fixed += 1
                total_changes += changes
            except Exception:
                errors += 1

        lines = ["✅ 字幕修正完成！\n"]
        lines.append(f"📂 目录: {audios_dir}")
        lines.append(f"📊 总计: {total} 个 SRT 文件")
        lines.append(f"🔧 已修正: {fixed} 个")
        lines.append(f"✏️  总修改: {total_changes} 处文字差异")
        lines.append(f"⏭️  无对应文本: {unchanged} 个")
        if errors:
            lines.append(f"⚠️  出错: {errors} 个")
        return "\n".join(lines)

    PUNCTUATION_CHARS = set(
        "，。！？、：；…—～（）【】《》\u201c\u201d\u2018\u2019"
        ",.!?:;-()[]{}<>'\""
    )

    @staticmethod
    def _strip_edge_punctuation(text: str) -> str:
        if not text:
            return text
        punct = FixSrtSkill.PUNCTUATION_CHARS
        start = 0
        end = len(text)
        while start < end and text[start] in punct:
            start += 1
        while end > start and text[end - 1] in punct:
            end -= 1
        return text[start:end]
    @staticmethod
    def _detect_project_id() -> str:
        pattern = os.path.join(WORKSPACE_DIR, "video-script-*.json")
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        for fp in files:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            pid = data.get("meta", {}).get("project_id", "")
            if pid:
                return pid
        return ""

    @staticmethod
    def _load_video_script(project_id: str) -> dict:
        pattern = os.path.join(WORKSPACE_DIR, "video-script-*.json")
        json_files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("meta", {}).get("project_id") == project_id:
                    return data
            except (json.JSONDecodeError, IOError):
                continue
        return {}

    @staticmethod
    def _build_caption_map(video_script: dict) -> dict:
        caption_map = {}
        for scene in video_script.get("script", []):
            for caption in scene.get("captions", []):
                audio = caption.get("audio", "")
                srt_text = caption.get("srt", "")
                if audio and srt_text:
                    caption_map[audio] = srt_text
        return caption_map

    def _fix_one_srt(self, srt_path: str, correct_text: str) -> int:
        segments = self._parse_srt(srt_path)
        if not segments:
            return 0

        whisper_texts = [seg["text"] for seg in segments]
        whisper_concat = "".join(whisper_texts)

        if whisper_concat == correct_text:
            return 0

        corrected_segments = self._align_and_correct(segments, whisper_concat, correct_text)

        changes = 0
        for seg, new_text in zip(segments, corrected_segments):
            new_text = self._strip_edge_punctuation(new_text)
            if seg["text"] != new_text:
                seg["text"] = new_text
                changes += 1

        if changes > 0:
            self._write_srt(srt_path, segments)

        return changes

    @staticmethod
    def _parse_srt(srt_path: str) -> list:
        segments = []
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        blocks = re.split(r'\n\s*\n', content)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = block.split('\n')
            if len(lines) < 3:
                continue
            try:
                int(lines[0].strip())
            except ValueError:
                continue

            time_match = re.match(
                r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})',
                lines[1]
            )
            if not time_match:
                continue

            start = time_match.group(1).replace(',', '.')
            end = time_match.group(2).replace(',', '.')
            text = '\n'.join(lines[2:])

            segments.append({
                "index": len(segments) + 1,
                "start": start,
                "end": end,
                "text": text,
            })

        return segments

    @staticmethod
    def _align_and_correct(segments: list, whisper_concat: str, correct_text: str) -> list:
        matcher = difflib.SequenceMatcher(None, whisper_concat, correct_text)
        matching_blocks = matcher.get_matching_blocks()

        corrected = []
        cursor = 0
        for seg in segments:
            seg_len = len(seg["text"])
            seg_start = cursor
            seg_end = cursor + seg_len
            cursor = seg_end

            correct_start = FixSrtSkill._map_position(seg_start, matching_blocks)
            correct_end = FixSrtSkill._map_position(seg_end, matching_blocks)

            if correct_end > correct_start:
                new_text = correct_text[correct_start:correct_end]
            else:
                new_text = seg["text"]

            corrected.append(new_text)

        return corrected

    @staticmethod
    def _map_position(pos: int, matching_blocks: list) -> int:
        for a_start, b_start, length in matching_blocks:
            if a_start <= pos < a_start + length:
                offset = pos - a_start
                return b_start + offset

        prev_end_a = 0
        prev_end_b = 0
        for a_start, b_start, length in matching_blocks:
            if pos <= a_start:
                gap = pos - prev_end_a
                if gap < 0:
                    gap = 0
                return prev_end_b + gap
            prev_end_a = a_start + length
            prev_end_b = b_start + length

        gap = pos - prev_end_a
        if gap < 0:
            gap = 0
        return prev_end_b + gap

    @staticmethod
    def _write_srt(srt_path: str, segments: list):
        lines = []
        for i, seg in enumerate(segments):
            lines.append(str(i + 1))
            start_fmt = seg["start"].replace('.', ',')
            end_fmt = seg["end"].replace('.', ',')
            lines.append(f"{start_fmt} --> {end_fmt}")
            lines.append(seg["text"])
            lines.append("")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def create_skill():
    return FixSrtSkill()