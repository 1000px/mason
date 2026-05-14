---
name: string_reverse
description: |
  反转字符串。当用户说"反转"、"倒序"、"反过来"时激活。
version: "1.0.0"
author: Mason Team
---

# 字符串反转

## 激活条件
- 用户说"反转xxx"、"把xxx倒过来"
- 用户说"倒序显示"、"反过来"

## 核心规则
- 直接将工具返回的结果输出给用户，不要添加额外格式或评论

## 执行流程
1. 调用 string_reverse skill
2. 将结果直接输出给用户