import os
import json
import glob
import uuid
import time
import shutil
import threading
import subprocess
import datetime
import logging
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")
SKILL_DIR = os.path.dirname(__file__)

ROLES_DIR = os.path.join(WORKSPACE_DIR, "audios", "roles")
SOUND_EFFECTS_DIR = os.path.join(WORKSPACE_DIR, "audios", "sound_effects")

SEC = 1000000


def _get_jianying_draft_dir() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return os.path.join(local_app_data, "JianyingPro", "User Data", "Projects", "com.lveditor.draft")
    return os.path.join(os.path.expanduser("~"), "AppData", "Local", "JianyingPro", "User Data", "Projects", "com.lveditor.draft")

SUBTITLE_STYLE_PRESETS = {
    1: {
        "name": "口播字幕",
        "description": "居中打字入场 + 轻微跳动循环 + 渐隐出场 + 白色描边",
        "intro": {
            "name": "居中打字",
            "effect_id": "20303987",
            "resource_id": "7265222187286532667",
            "duration_us": 500000,
        },
        "loop": {
            "name": "轻微跳动",
            "effect_id": "1644525",
            "resource_id": "6884155832838132231",
            "duration_us": 500000,
        },
        "outro": {
            "name": "渐隐",
            "effect_id": "1644600",
            "resource_id": "6724919382104871427",
            "duration_us": 500000,
        },
        "style": {
            "size": 5.0,
            "bold": False,
            "color": [1.0, 1.0, 1.0],
            "stroke_color": [0.0, 0.0, 0.0],
            "stroke_width": 40.0,
            "stroke_alpha": 1.0,
        },
    },
    2: {
        "name": "强调关键词",
        "description": "弹入入场 + 闪烁循环 + 弹出出场 + 黄色阴影",
        "intro": {
            "name": "弹入",
            "effect_id": "1644313",
            "resource_id": "6887482184844710413",
            "duration_us": 500000,
        },
        "loop": {
            "name": "闪烁",
            "effect_id": "1644514",
            "resource_id": "6724921437930394120",
            "duration_us": 500000,
        },
        "outro": {
            "name": "弹出",
            "effect_id": "1644648",
            "resource_id": "6887482090351235592",
            "duration_us": 500000,
        },
        "style": {
            "size": 6.0,
            "bold": True,
            "color": [1.0, 0.85, 0.0],
            "stroke_color": [0.0, 0.0, 0.0],
            "stroke_width": 30.0,
            "stroke_alpha": 0.8,
            "shadow": {"alpha": 0.5, "color": [0.0, 0.0, 0.0], "diffuse": 20.0, "distance": 8.0, "angle": -45.0},
        },
    },
    3: {
        "name": "片头标题",
        "description": "水墨晕开入场 + 扫光循环 + 模糊出场 + 大字号粗体",
        "intro": {
            "name": "水墨晕开",
            "effect_id": "22734325",
            "resource_id": "7278295995362841145",
            "duration_us": 1200000,
        },
        "loop": {
            "name": "扫光",
            "effect_id": "1520868",
            "resource_id": "7051843475892867598",
            "duration_us": 500000,
        },
        "outro": {
            "name": "模糊",
            "effect_id": "1644652",
            "resource_id": "6923094772907250189",
            "duration_us": 500000,
        },
        "style": {
            "size": 8.0,
            "bold": True,
            "color": [1.0, 1.0, 1.0],
            "stroke_color": [0.0, 0.0, 0.0],
            "stroke_width": 50.0,
            "stroke_alpha": 1.0,
        },
    },
    4: {
        "name": "恐怖悬疑",
        "description": "故障打字机入场 + 色差故障循环 + 渐隐出场 + 红色描边",
        "intro": {
            "name": "故障打字机",
            "effect_id": "1644308",
            "resource_id": "6870061463243854350",
            "duration_us": 500000,
        },
        "loop": {
            "name": "色差故障",
            "effect_id": "1644522",
            "resource_id": "6835878163575214605",
            "duration_us": 500000,
        },
        "outro": {
            "name": "渐隐",
            "effect_id": "1644600",
            "resource_id": "6724919382104871427",
            "duration_us": 500000,
        },
        "style": {
            "size": 5.0,
            "bold": False,
            "color": [1.0, 0.2, 0.2],
            "stroke_color": [0.6, 0.0, 0.0],
            "stroke_width": 40.0,
            "stroke_alpha": 1.0,
        },
    },
    5: {
        "name": "文艺风",
        "description": "逐字显影入场 + 摇摆循环 + 水墨晕开出场 + 暖色文字",
        "intro": {
            "name": "逐字显影",
            "effect_id": "1644339",
            "resource_id": "7038882772450021896",
            "duration_us": 500000,
        },
        "loop": {
            "name": "摇摆",
            "effect_id": "1644515",
            "resource_id": "6724920869363126795",
            "duration_us": 500000,
        },
        "outro": {
            "name": "水墨晕开",
            "effect_id": "22734371",
            "resource_id": "7278296130432012857",
            "duration_us": 1200000,
        },
        "style": {
            "size": 5.0,
            "bold": False,
            "color": [1.0, 0.9, 0.7],
            "stroke_color": [0.3, 0.2, 0.1],
            "stroke_width": 30.0,
            "stroke_alpha": 0.6,
        },
    },
}


class CreateDraftArgs(BaseModel):
    script_file: str = Field(
        default="",
        description="video-script-*.json 文件名（不含路径），例如 'video-script-1744935480.json'。留空则自动选择最新的脚本文件。",
    )
    subtitle_style: int = Field(
        default=0,
        description="字幕风格序号（1-5），0 表示不启用特效。",
    )


class CreateDraftSkill(BaseSkill):
    name = "create_draft"
    description = "根据 video-script-*.json 脚本文件自动生成剪映专业版视频草稿（draft_content.json + draft_meta_info.json）。"
    args_schema = CreateDraftArgs

    permissions = {
        "network": False,
        "filesystem": True,
        "max_cpu": 0.3,
        "max_memory": 512,
    }

    def execute(self, script_file: str = "", subtitle_style: int = 0) -> str:
        running_status = self._get_running_status()
        if running_status:
            return running_status

        if subtitle_style == 0:
            existing = self._scan_jianying_drafts()
            if existing:
                return existing

            lines = ["🎨 请选择字幕特效风格（输入序号）：\n"]
            for idx in sorted(SUBTITLE_STYLE_PRESETS.keys()):
                preset = SUBTITLE_STYLE_PRESETS[idx]
                lines.append(f"  {idx}. {preset['name']} — {preset['description']}")
            lines.append(f"\n💡 用法：告诉我\"用风格 N 生成草稿\"即可（N 为 1-5）")
            return "\n".join(lines)

        if subtitle_style not in SUBTITLE_STYLE_PRESETS:
            return f"❌ 无效的字幕风格序号: {subtitle_style}，有效范围: 1-5"

        script_path = self._resolve_script_path(script_file)
        if not script_path:
            return "❌ 未找到 video-script-*.json 文件，请先使用视频脚本生成工具创建脚本。"

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        status_path = os.path.join(WORKSPACE_DIR, f"_draft_status_{timestamp}.json")
        self._write_status(status_path, "running", 0, 1, "正在读取脚本文件...")

        thread = threading.Thread(
            target=self._run_background,
            args=(script_path, status_path, timestamp, subtitle_style),
            daemon=True,
        )
        thread.start()

        preset_name = SUBTITLE_STYLE_PRESETS[subtitle_style]["name"]
        script_name = os.path.basename(script_path)
        return (
            f"🎬 草稿生成任务已启动（脚本: {script_name}，字幕风格: {preset_name}），后台运行中...\n"
            f"随时问我\"草稿生成进度\"查看状态。"
        )

    def _resolve_script_path(self, script_file: str) -> str:
        if script_file:
            path = os.path.join(WORKSPACE_DIR, script_file)
            if os.path.isfile(path):
                return path
            return ""

        pattern = os.path.join(WORKSPACE_DIR, "video-script-*.json")
        files = glob.glob(pattern)
        if not files:
            return ""
        return max(files, key=os.path.getmtime)

    def _run_background(self, script_path: str, status_path: str, timestamp: str, subtitle_style: int = 0):
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._write_status(status_path, "error", 0, 1, f"读取脚本文件失败: {e}")
            self._notify_user(0, 1, error=f"读取脚本文件失败: {e}")
            return

        self._write_status(status_path, "running", 0, 1, "正在读取 project_id...")

        project_id = script_data.get("meta", {}).get("project_id", "")
        if not project_id:
            self._write_status(status_path, "error", 0, 1, "脚本中缺少 meta.project_id，请先运行语音生成工具。")
            self._notify_user(0, 1, error="脚本中缺少 meta.project_id")
            return

        project_audios_dir = os.path.join(WORKSPACE_DIR, project_id, "audios")
        project_resources_dir = os.path.join(WORKSPACE_DIR, project_id, "resources")

        jianying_draft_dir = _get_jianying_draft_dir()
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        draft_name = f"{date_str}-{project_id}"
        draft_dir = os.path.join(jianying_draft_dir, draft_name)
        os.makedirs(draft_dir, exist_ok=True)

        self._write_status(status_path, "running", 0, 1, "正在拷贝图片素材...")

        for scene in script_data.get("script", []):
            image_name = scene.get("image_name", "")
            if not image_name:
                continue
            src = os.path.join(project_resources_dir, image_name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(draft_dir, image_name))

        self._write_status(status_path, "running", 0, 1, "正在构建草稿内容...")

        try:
            draft_content = self._build_draft_content(
                script_data, project_id, project_audios_dir, draft_dir, subtitle_style
            )
            draft_meta = self._build_draft_meta(script_data, project_id, draft_dir, project_audios_dir)
        except Exception as e:
            logger.exception("构建草稿失败")
            self._write_status(status_path, "error", 0, 1, f"构建草稿失败: {e}")
            self._notify_user(0, 1, error=f"构建草稿失败: {e}")
            return

        self._write_status(status_path, "running", 0, 1, "正在保存草稿文件...")

        content_path = os.path.join(draft_dir, "draft_content.json")
        meta_path = os.path.join(draft_dir, "draft_meta_info.json")

        try:
            draft_content.dump(content_path)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(draft_meta, f, ensure_ascii=False, indent=2)
        except IOError as e:
            self._write_status(status_path, "error", 0, 1, f"保存草稿文件失败: {e}")
            self._notify_user(0, 1, error=f"保存草稿文件失败: {e}")
            return

        total_duration_us = draft_content.duration
        total_duration_s = total_duration_us / SEC
        caption_count = sum(len(scene.get("captions", [])) for scene in script_data.get("script", []))
        scene_count = len(script_data.get("script", []))

        summary = (
            f"🎬 剪映草稿已生成！\n\n"
            f"📁 草稿名称: {draft_name}\n"
            f"📁 草稿目录: {draft_dir}\n"
            f"📄 draft_content.json\n"
            f"📄 draft_meta_info.json\n"
            f"📊 场景数: {scene_count}\n"
            f"💬 字幕数: {caption_count}\n"
            f"⏱️ 总时长: {total_duration_s:.1f} 秒\n"
            f"🔑 project_id: {project_id}\n\n"
            f"💡 打开剪映专业版即可看到草稿「{draft_name}」！"
        )

        self._write_status(status_path, "done", 1, 1, summary, draft_dir=draft_dir)
        self._notify_user(1, 1)

    def _build_draft_content(self, script_data: dict, project_id: str,
                              project_audios_dir: str, draft_dir: str,
                              subtitle_style: int = 0):
        from pyJianYingDraft.script_file import ScriptFile
        from pyJianYingDraft.track import TrackType
        from pyJianYingDraft.text_segment import TextSegment, TextStyle, TextBorder, TextShadow
        from pyJianYingDraft.segment import ClipSettings
        from pyJianYingDraft.audio_segment import AudioSegment
        from pyJianYingDraft.local_materials import AudioMaterial, VideoMaterial
        from pyJianYingDraft.time_util import Timerange
        from pyJianYingDraft.metadata import TextIntro, TextOutro, TextLoopAnim
        from pyJianYingDraft.video_segment import VideoSegment, Transition
        from pyJianYingDraft.metadata.transition_meta import TransitionType

        script = ScriptFile(width=1920, height=1080, fps=30, maintrack_adsorb=True)

        script.add_track(TrackType.video, "main_video")
        script.add_track(TrackType.audio, "main_audio")
        script.add_track(TrackType.text, "subtitles")

        preset = SUBTITLE_STYLE_PRESETS.get(subtitle_style) if subtitle_style else None

        intro_anim_enum = None
        outro_anim_enum = None
        loop_anim_enum = None
        if preset:
            intro_anim_enum = self._find_animation_enum(TextIntro, preset["intro"]["effect_id"])
            outro_anim_enum = self._find_animation_enum(TextOutro, preset["outro"]["effect_id"])
            loop_anim_enum = self._find_animation_enum(TextLoopAnim, preset["loop"]["effect_id"])

        current_time_us = 0
        script_scenes = script_data.get("script", [])

        for scene_idx, scene in enumerate(script_scenes):
            captions = scene.get("captions", [])
            scene_start_us = current_time_us

            for cap_idx, caption in enumerate(captions):
                audio_file = caption.get("audio", "")
                audio_length_str = caption.get("audio_length", "0")
                audio_length_s = self._parse_audio_length(audio_length_str)
                audio_duration_us = int(audio_length_s * SEC)

                audio_path = os.path.join(project_audios_dir, audio_file) if audio_file else ""

                if audio_file and os.path.isfile(audio_path):
                    try:
                        audio_material = AudioMaterial(audio_path)
                        audio_timerange = Timerange(current_time_us, audio_duration_us)
                        audio_segment = AudioSegment(
                            audio_material,
                            audio_timerange,
                            volume=1.0,
                        )
                        script.add_segment(audio_segment, "main_audio")
                    except Exception as e:
                        logger.warning("添加音频片段失败 (%s): %s", audio_file, e)

                srt_file = audio_file.replace(".mp3", "-sub.srt") if audio_file else ""
                srt_path = os.path.join(project_audios_dir, srt_file)
                srt_entries = self._parse_srt_file(srt_path)

                if srt_entries:
                    for entry in srt_entries:
                        entry_start_us = entry["start_us"]
                        entry_end_us = entry["end_us"]
                        if entry_start_us >= audio_duration_us:
                            continue
                        if entry_end_us > audio_duration_us:
                            entry_end_us = audio_duration_us
                        entry_start = current_time_us + entry_start_us
                        entry_duration = entry_end_us - entry_start_us
                        if entry_duration <= 0:
                            continue
                        self._add_text_segment_pyjd(
                            script, entry["text"], entry_start, entry_duration,
                            preset, intro_anim_enum, outro_anim_enum, loop_anim_enum,
                        )
                else:
                    text_content = caption.get("srt", "")
                    if text_content:
                        self._add_text_segment_pyjd(
                            script, text_content, current_time_us, audio_duration_us,
                            preset, intro_anim_enum, outro_anim_enum, loop_anim_enum,
                        )

                current_time_us += audio_duration_us

            scene_duration_us = current_time_us - scene_start_us

            image_name = scene.get("image_name", "")
            if image_name:
                image_path = os.path.join(draft_dir, image_name)
                if os.path.isfile(image_path):
                    try:
                        image_material = VideoMaterial(image_path)
                        image_timerange = Timerange(scene_start_us, scene_duration_us)
                        image_segment = VideoSegment(image_material, image_timerange)
                        script.add_segment(image_segment, "main_video")
                    except Exception as e:
                        logger.warning("添加图片素材失败 (%s): %s", image_name, e)

            if scene_idx < len(script_scenes) - 1:
                transition_duration_us = int(0.5 * SEC)
                transition = Transition(TransitionType.叠化, duration=transition_duration_us)
                script.materials.transitions.append(transition)

        return script

    def _add_text_segment_pyjd(self, script, text: str, start_us: int, duration_us: int,
                                preset: dict = None,
                                intro_anim_enum=None, outro_anim_enum=None, loop_anim_enum=None):
        from pyJianYingDraft.text_segment import TextSegment, TextStyle, TextBorder, TextShadow
        from pyJianYingDraft.segment import ClipSettings
        from pyJianYingDraft.time_util import Timerange

        if preset:
            ps = preset["style"]
            style = TextStyle(
                size=ps.get("size", 5.0),
                bold=ps.get("bold", False),
                color=tuple(ps["color"]),
                align=0,
            )

            border = None
            if ps.get("stroke_color"):
                border = TextBorder(
                    alpha=ps.get("stroke_alpha", 1.0),
                    color=tuple(ps["stroke_color"]),
                    width=ps.get("stroke_width", 40.0),
                )

            shadow = None
            if "shadow" in ps:
                sh = ps["shadow"]
                shadow = TextShadow(
                    alpha=sh.get("alpha", 1.0),
                    color=tuple(sh["color"]),
                    diffuse=sh.get("diffuse", 15.0),
                    distance=sh.get("distance", 5.0),
                    angle=sh.get("angle", -45.0),
                )
        else:
            style = TextStyle(size=5.0, color=(1.0, 1.0, 1.0), align=0)
            border = None
            shadow = None

        clip_settings = ClipSettings(transform_y=-0.8)
        timerange = Timerange(start_us, duration_us)

        text_segment = TextSegment(
            text,
            timerange,
            style=style,
            clip_settings=clip_settings,
            border=border,
            shadow=shadow,
        )

        if preset and intro_anim_enum:
            intro_dur = min(preset["intro"]["duration_us"], duration_us)
            text_segment.add_animation(intro_anim_enum, duration=intro_dur)
        if preset and outro_anim_enum:
            outro_dur = min(preset["outro"]["duration_us"], duration_us)
            text_segment.add_animation(outro_anim_enum, duration=outro_dur)
        if preset and loop_anim_enum:
            text_segment.add_animation(loop_anim_enum)

        script.add_segment(text_segment, "subtitles")

    @staticmethod
    def _find_animation_enum(enum_cls, effect_id: str):
        for member in enum_cls:
            if member.value.effect_id == effect_id:
                return member
        return None

    def _build_draft_meta(self, script_data: dict, project_id: str, draft_dir: str, project_audios_dir: str) -> dict:
        with open(os.path.join(SKILL_DIR, "draft_meta_info_template.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)

        now = int(time.time())
        now_ms = int(time.time() * 1000)

        meta["draft_id"] = uuid.uuid4().hex
        meta["draft_name"] = project_id[:8]
        meta["draft_root_path"] = os.path.dirname(draft_dir)
        meta["draft_fold_path"] = draft_dir
        meta["tm_draft_create"] = now
        meta["tm_draft_modified"] = now

        total_duration_us = 0
        audio_materials_list = meta["draft_materials"][0]["value"]

        script_scenes = script_data.get("script", [])
        for scene in script_scenes:
            for caption in scene.get("captions", []):
                audio_file = caption.get("audio", "")
                audio_length_str = caption.get("audio_length", "0")
                audio_length_s = self._parse_audio_length(audio_length_str)
                audio_duration_us = int(audio_length_s * SEC)

                audio_path = os.path.join(project_audios_dir, audio_file) if audio_file else ""

                audio_materials_list.append({
                    "create_time": now,
                    "duration": audio_duration_us,
                    "extra_info": audio_file,
                    "file_Path": audio_path,
                    "height": 0,
                    "id": uuid.uuid4().hex,
                    "import_time": now,
                    "import_time_ms": now_ms,
                    "item_source": 1,
                    "md5": "",
                    "metetype": "music",
                    "roughcut_time_range": {"duration": audio_duration_us, "start": -1},
                    "sub_time_range": {"duration": -1, "start": -1},
                    "type": 0,
                    "width": 0,
                })

                total_duration_us += audio_duration_us

            scene_duration_us = sum(
                int(self._parse_audio_length(c.get("audio_length", "0")) * SEC)
                for c in scene.get("captions", [])
            )

            image_name = scene.get("image_name", "")
            if image_name:
                image_path = os.path.join(draft_dir, image_name)
                if os.path.isfile(image_path):
                    audio_materials_list.append({
                        "create_time": now,
                        "duration": scene_duration_us,
                        "extra_info": image_name,
                        "file_Path": image_path,
                        "height": 0,
                        "id": uuid.uuid4().hex,
                        "import_time": now,
                        "import_time_ms": now_ms,
                        "item_source": 1,
                        "md5": "",
                        "metetype": "photo",
                        "roughcut_time_range": {"duration": -1, "start": -1},
                        "sub_time_range": {"duration": -1, "start": -1},
                        "type": 0,
                        "width": 0,
                    })

        meta["tm_duration"] = total_duration_us

        return meta

    @staticmethod
    def _parse_audio_length(audio_length_str: str) -> float:
        if not audio_length_str:
            return 0.0
        normalized = audio_length_str.replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_srt_file(srt_path: str) -> list:
        entries = []
        if not os.path.isfile(srt_path):
            return entries

        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = content.strip().split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue

            time_line = lines[1]
            text = "\n".join(lines[2:])

            try:
                start_str, end_str = time_line.split(" --> ")
                start_us = CreateDraftSkill._srt_time_to_us(start_str)
                end_us = CreateDraftSkill._srt_time_to_us(end_str)
            except (ValueError, IndexError):
                continue

            entries.append({
                "start_us": start_us,
                "end_us": end_us,
                "text": text,
            })

        return entries

    @staticmethod
    def _srt_time_to_us(time_str: str) -> int:
        time_str = time_str.strip()
        h, m, rest = time_str.split(":")
        s, ms = rest.split(",")
        total_s = int(h) * 3600 + int(m) * 60 + int(s)
        total_ms = int(ms)
        return total_s * SEC + total_ms * 1000

    @staticmethod
    def _write_status(status_path: str, state: str, done: int, total: int, message: str, draft_dir: str = ""):
        try:
            payload = {
                "state": state,
                "done": done,
                "total": total,
                "message": message,
            }
            if draft_dir:
                payload["draft_dir"] = draft_dir
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except IOError:
            pass

    @staticmethod
    def _notify_user(done: int, total: int, error: str = None):
        if error:
            msg = f"[Mason] 剪映草稿生成出错: {error[:100]}"
        else:
            msg = f"[Mason] 剪映草稿已生成！"

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
    def _extract_project_id_from_message(message: str) -> str:
        import re
        match = re.search(r'project_id:\s*([a-f0-9]+)', message)
        return match.group(1) if match else ""

    @staticmethod
    def _get_running_status() -> str:
        pattern = os.path.join(WORKSPACE_DIR, "_draft_status_*.json")
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
            return f"🎬 草稿生成进行中：{done}/{total} ({pct})\n状态: {message}"

        if state == "done":
            draft_dir = s.get("draft_dir", "")
            if draft_dir and not os.path.isdir(draft_dir):
                try:
                    os.remove(latest)
                except OSError:
                    pass
                return ""
            return message

        if state == "error":
            return f"❌ 草稿生成出错：{done}/{total}\n{message}"

        return ""

    @staticmethod
    def _scan_jianying_drafts() -> str:
        jianying_draft_dir = _get_jianying_draft_dir()
        if not os.path.isdir(jianying_draft_dir):
            return ""

        drafts = []
        for name in sorted(os.listdir(jianying_draft_dir), reverse=True):
            draft_path = os.path.join(jianying_draft_dir, name)
            if not os.path.isdir(draft_path):
                continue
            content_file = os.path.join(draft_path, "draft_content.json")
            meta_file = os.path.join(draft_path, "draft_meta_info.json")
            if not os.path.isfile(content_file) or not os.path.isfile(meta_file):
                continue

            size_kb = 0
            try:
                size_kb = (os.path.getsize(content_file) + os.path.getsize(meta_file)) / 1024
            except OSError:
                pass

            mtime = os.path.getmtime(draft_path)
            mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

            drafts.append({
                "name": name,
                "path": draft_path,
                "mtime": mtime_str,
                "size_kb": size_kb,
            })

        if not drafts:
            return ""

        lines = ["📁 剪映草稿目录中已有以下草稿：\n"]
        for i, d in enumerate(drafts[:10], 1):
            lines.append(f"  {i}. {d['name']}")
            lines.append(f"     📂 {d['path']}")
            lines.append(f"     🕐 {d['mtime']}  |  📦 {d['size_kb']:.0f} KB")

        if len(drafts) > 10:
            lines.append(f"\n  ... 还有 {len(drafts) - 10} 个草稿")

        lines.append(f"\n💡 打开剪映专业版即可看到这些草稿。")
        return "\n".join(lines)


def create_skill():
    return CreateDraftSkill()