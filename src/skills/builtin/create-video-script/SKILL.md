---
name: create_video_script
description: |
  生成视频脚本：随机选择一个民间故事模板，生成完整的 video-script-*.json 文件。
  当用户说"生成视频脚本"、"创作民间故事"、"写个故事脚本"、"来段评书"时激活。
version: "1.0.0"
author: Mason Team
---

# 生成视频脚本

## 激活条件
- 用户说"生成视频脚本"、"创作民间故事"
- 用户说"写个故事脚本"、"来段评书"
- 用户说"说书先生"、"讲个民间故事"

## 功能说明

调用 `execute()` 后，skill 会：
1. 从内置故事模板中随机选择一个（如《画中仙》、《石狮开口》等）
2. 生成完整的 video-script JSON 文件，包含 `meta.roles` 和 `script` 数组
3. 文件保存到 `workspace/video-script-{timestamp}.json`
4. 返回生成结果摘要（文件路径、故事标题、角色、段落数等）

## JSON 格式

```json
{
  "meta": {
    "roles": ["旁白 default", "角色名 男", "角色名 女"]
  },
  "script": [
    {
      "text": "一级拆分文本，300-600字",
      "image_prompt": "AI生成图片提示词",
      "captions": [
        { "role": "旁白", "srt": "旁白文案..." },
        { "role": "角色名", "gender": "男", "srt": "对白..." }
      ]
    }
  ]
}
```

## 后续操作

生成脚本后，用户可以继续：
- "批量生成语音" — 为所有角色配音
- "语音转字幕" — 生成精确时间轴字幕
- "生成剪映草稿" — 一键生成剪映专业版草稿