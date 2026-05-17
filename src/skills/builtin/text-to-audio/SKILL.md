---
name: text_to_audio
description: |
  根据脚本JSON批量将文本转为语音，使用IndexTTS 2.0进行音色克隆。
  扫描 workspace 目录下最新的 video-script-*.json 文件，
  遍历 script.captions，根据角色性别匹配参考音频，调用 IndexTTS 2.0 生成语音。
  当用户说"根据脚本批量转语音"、"批量生成语音"、"脚本转音频"时激活。
  也用于查询语音合成进度，当用户说"语音合成进度"、"生成到哪了"、"语音生成完了吗"时激活。
version: "1.0.0"
author: Mason Team
---

# 脚本批量转语音

## 激活条件
- 用户说"根据脚本批量转语音"、"批量生成语音"
- 用户说"脚本转音频"、"生成配音"
- 用户说"把脚本转成语音"
- 用户说"语音合成进度"、"生成到哪一步了"、"语音生成完了吗"、"看看语音生成状态"

## 核心规则
- 直接将工具返回的结果输出给用户，不要添加额外格式或评论
- 如果后台有正在运行的语音合成任务，自动返回进度信息
- 如果没有运行中的任务，则启动新的批量语音合成
- 自动扫描 workspace 目录下最新的 video-script-*.json
- 遍历所有 script.captions，跳过 srt 为空的条目
- 生成后自动更新 JSON 中的 audio 和 audio_length 字段

## 前置条件
1. IndexTTS 2.0 已克隆到 src/third_party/index-tts/
2. 已执行 uv sync --all-extras 安装依赖
3. 模型已下载到 checkpoints/ 目录
4. workspace/audios/roles/ 下已准备好参考音频

## 执行流程
1. 检查是否有运行中的语音合成任务，有则返回进度
2. 扫描 workspace 目录，找到最新的 video-script-*.json
3. 解析 JSON，构建角色→参考音频映射
4. 将任务写入 `workspace/_tts_queue/` 队列目录
5. 自动启动 TTS 守护进程（首次需加载模型约50秒，后续复用）
6. 守护进程处理任务，skill 轮询结果文件
7. 更新 JSON 中的 audio 和 audio_length 字段
8. 将结果直接输出给用户

## 守护进程架构
- 守护进程 `tts_daemon.py` 在后台常驻运行，模型只加载一次
- 任务通过 `workspace/_tts_queue/job_*.json` 文件队列提交
- 结果写入 `workspace/_tts_queue/job_*.result.json`
- PID 文件: `workspace/_tts_queue/tts_daemon.pid`
- 日志文件: `workspace/_tts_queue/daemon.log` / `daemon_err.log`