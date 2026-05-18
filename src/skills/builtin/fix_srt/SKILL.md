---
name: fix_srt
description: |
  修正 SRT 字幕文件中的错别字。
  基于 video-script-*.json 中的原始正确文本，校正 Whisper 语音转录产生的错别字。
  只修改字幕文字内容，保留所有时间戳不变。
  当用户说"修正字幕"、"改错别字"、"纠正字幕"、"修复字幕错字"、"字幕有错别字"时激活。
version: "1.0.0"
author: Mason Team
---

# 修正字幕错别字

## 激活条件
- 用户说"修正字幕"、"改错别字"、"纠正字幕"、"修复字幕错字"
- 用户说"字幕有错别字"、"帮我改一下字幕的文字"
- 用户说"修正 srt"、"修正字幕错别字"

## 核心规则
- **用户不需要指定任何文件或目录！** skill 会自动完成所有定位工作
- 直接将工具返回的结果输出给用户，不要添加额外格式或评论
- **不要向用户询问任何问题**，直接调用 fix_srt skill 即可
- skill 自动从 workspace 下最新的 video-script-*.json 读取 project_id
- skill 自动定位 workspace/[project_id]/audios/ 目录下的所有 -sub.srt 文件
- skill 自动根据 JSON 中各 caption 的 srt 字段（正确文本）修正 Whisper 转录的错别字
- **只修改字幕文字内容，绝不修改任何时间戳**
- 将修正后的 SRT 写回原文件

## 执行流程
1. 收到用户请求后，**立即调用 fix_srt skill，不传任何参数**
2. skill 内部自动完成：检测 project_id → 扫描 SRT 文件 → 文本对齐修正 → 写回文件
3. 直接将 skill 返回的结果输出给用户