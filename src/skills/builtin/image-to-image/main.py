import os
import uuid
import base64
import requests
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "output", "images")
OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

POLLINATIONS_API = "https://api.pollinations.ai/prompt"


class ImageToImageArgs(BaseModel):
    image_path: str = Field(description="本地输入图片的完整文件路径")
    prompt: str = Field(description="修改描述文本，例如：'改成油画风格'、'换成晚上的场景'")
    strength: float = Field(default=0.7, description="变换强度（0-1），越大修改越多")
    width: int = Field(default=1024, description="输出图片宽度")
    height: int = Field(default=1024, description="输出图片高度")


class ImageToImageSkill(BaseSkill):
    name = "image_to_image"
    description = "基于已有图片修改/重绘生成新图片（图生图）。传入本地图片路径和修改描述。"
    args_schema = ImageToImageArgs

    permissions = {
        "network": True,
        "filesystem": True,
        "max_cpu": 0.3,
        "max_memory": 128,
    }

    def execute(
        self,
        image_path: str = "",
        prompt: str = "",
        strength: float = 0.7,
        width: int = 1024,
        height: int = 1024,
    ) -> str:
        if not image_path or not os.path.exists(image_path):
            return f"❌ 输入图片不存在: {image_path}"
        if not prompt:
            return "❌ 请提供修改描述（prompt）。"

        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            payload = {
                "prompt": prompt,
                "image": image_b64,
                "image_strength": strength,
                "width": width,
                "height": height,
                "nologo": True,
            }

            resp = requests.post(POLLINATIONS_API, json=payload, timeout=120)
            resp.raise_for_status()

            if resp.status_code != 200:
                return f"❌ 生成失败: HTTP {resp.status_code}"

            filename = f"{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(OUTPUT_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(resp.content)

            return f"✅ 图片已生成！\n📁 保存路径: {filepath}\n🔍 原图片: {image_path}\n✨ Prompt: {prompt}"

        except FileNotFoundError:
            return f"❌ 文件未找到: {image_path}"
        except requests.RequestException as e:
            return f"❌ 图片生成失败: {str(e)}"
        except Exception as e:
            return f"❌ 异常: {str(e)}"