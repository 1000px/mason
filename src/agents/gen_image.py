from .base import BaseAgent

GEN_IMAGE_PROMPT = """You are Mason's Image Generation Agent.
You are specialized in generating images from text prompts (text-to-image) 
and editing/transforming existing images (image-to-image).

When the user asks to:
- "画一幅画"、"生成图片"、"创作图像" → use text_to_image skill
- "修改图片"、"重绘"、"基于这张图生成" → use image_to_image skill

Always use the appropriate tool to generate the image, don't just describe what you would do.
"""

class GenImageAgent(BaseAgent):
    def __init__(self):
        super().__init__(GEN_IMAGE_PROMPT)
        self.name = "gen_image"
        self.description = "Image generation agent for text-to-image and image-to-image tasks."
