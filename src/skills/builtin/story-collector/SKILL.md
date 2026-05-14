---
name: story_collector
description: |
  打开故事收集窗口，录入故事的标题、作者、标签和正文，保存到数据库。
  当用户说"故事收集"、"录入故事"、"收集故事"时激活。
version: "1.0.0"
author: Mason Team
---

# 故事收集

## 激活条件
- 用户说"故事收集"、"录入故事"、"收集故事"
- 用户说"我要录入一个故事"

## 核心规则
- 调用 story_collector skill 后会弹出 GUI 窗口
- 用户填写完毕后点击保存，数据存入 MySQL
- 直接将工具返回的结果输出给用户

## 执行流程
1. 调用 story_collector skill
2. 等待用户操作 GUI 窗口
3. 将结果直接输出给用户