# create-draft

## 功能

根据 `video-script-*.json` 脚本文件自动生成剪映专业版视频草稿。

## 工作流程

1. 读取 `workspace/video-script-*.json` 脚本文件
2. 若脚本中无 `project_id`，自动生成 UUID 并写回脚本文件
3. 在 `workspace/{project_id}/` 目录下创建草稿文件：
   - `draft_content.json` — 包含音频轨道、字幕轨道、视频轨道及所有素材
   - `draft_meta_info.json` — 草稿元信息
4. 任务在后台运行，可通过询问"草稿生成进度"查看状态
5. 完成后弹出 Windows 通知提醒

## 生成的草稿结构

### 音频轨道 (audio)
- 每个 caption 生成一个音频片段，引用 `workspace/audios/` 下的音频文件
- 自动关联 speed、beats、sound_channel_mappings、vocal_separations 素材

### 字幕轨道 (text)
- 每个 caption 生成一个字幕片段，内容为 `srt` 字段
- 默认样式：白色字体、居中、字号 5.0

### 视频轨道 (video)
- 预留，后续版本支持图片/视频素材

## 使用方式

```
create_draft
```

或指定脚本文件：

```
create_draft script_file="video-script-1744935480.json"
```

## 依赖

无外部依赖，纯 Python 标准库实现。