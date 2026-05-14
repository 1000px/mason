---
name: image_to_image
description: |
  图生图：基于输入图片修改/重绘生成新图片。当用户说"修改这张图"、"重绘"、"改风格"时激活。
version: "1.0.0"
author: Mason Team
---

# 图生图

## 激活条件
- 用户说"基于这张图生成"、"修改这张图片"
- 用户说"重绘"、"改风格"、"p图"

## 核心规则
- 直接将工具返回的结果输出给用户，不要添加额外格式或评论
- 生成的图片会保存到 output/images/ 目录

## 执行流程
1. 调用 image_to_image skill，传入 image_path（本地图片路径）和 prompt（修改描述）
2. 将结果直接输出给用户