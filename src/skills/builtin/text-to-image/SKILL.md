---
name: text_to_image
description: |
  文生图：根据文字描述生成图片。当用户说"画一幅"、"生成图片"、"创作图像"时激活。
version: "1.0.0"
author: Mason Team
---

# 文生图

## 激活条件
- 用户说"画一幅xxx"、"生成一张xxx的图片"
- 用户说"帮我创作xxx的图像"

## 核心规则
- 直接将工具返回的结果输出给用户，不要添加额外格式或评论
- 生成的图片会保存到 output/images/ 目录

## 执行流程
1. 调用 text_to_image skill，传入 prompt 参数
2. 将结果直接输出给用户