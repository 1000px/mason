import os
import uuid
import requests
from urllib.parse import quote
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "output", "images")
OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


class TextToImageArgs(BaseModel):
    prompt: str = Field(description="图片描述文本，例如：'a beautiful sunset over the ocean, oil painting style'")
    width: int = Field(default=1024, description="图片宽度（像素）")
    height: int = Field(default=1024, description="图片高度（像素）")


class TextToImageSkill(BaseSkill):
    name = "text_to_image"
    description = "根据文字描述生成图片（文生图）。传入 prompt 描述你想要生成的图像。"
    args_schema = TextToImageArgs

    permissions = {
        "network": True,
        "filesystem": True,
        "max_cpu": 0.3,
        "max_memory": 128,
    }

    def execute(self, prompt: str = "", width: int = 1024, height: int = 1024) -> str:
        if not prompt:
            return "❌ 请提供图片描述（prompt）。"

        encoded_prompt = quote(prompt, safe="")
        url = POLLINATIONS_URL.format(prompt=encoded_prompt)
        url += f"?width={width}&height={height}&nologo=true"

        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            filename = f"{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(OUTPUT_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(resp.content)

            return f"✅ 图片已生成！\n📁 保存路径: {filepath}\n🌐 在线链接: {url}"

        except requests.RequestException as e:
            return f"❌ 图片生成失败: {str(e)}"