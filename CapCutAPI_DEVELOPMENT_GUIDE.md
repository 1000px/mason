# CapCutAPI-Complete 完整开发指南

> CapCutAPI_DEVELOPMENT_GUIDE.md

> **文档用途**：本文档旨在帮助一个新的 AI Agent 或开发者，从零开始理解并复刻一个功能相同的视频编辑 API 服务产品。按照本文档的指引，你可以一步步引导用户完成整个项目的开发。

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈与依赖](#2-技术栈与依赖)
3. [项目完整结构](#3-项目完整结构)
4. [核心架构设计](#4-核心架构设计)
5. [文件逐一详解](#5-文件逐一详解)
   - [5.1 依赖配置文件](#51-依赖配置文件)
   - [5.2 Docker 部署文件](#52-docker-部署文件)
   - [5.3 核心库 pyJianYingDraft](#53-核心库-pyjianyingdraft)
   - [5.4 HTTP API 服务器](#54-http-api-服务器)
   - [5.5 MCP 协议服务器](#55-mcp-协议服务器)
   - [5.6 草稿管理模块](#56-草稿管理模块)
   - [5.7 视频轨道管理模块](#57-视频轨道管理模块)
   - [5.8 音频轨道管理模块](#58-音频轨道管理模块)
   - [5.9 文字与字幕管理模块](#59-文字与字幕管理模块)
   - [5.10 特效与转场管理模块](#510-特效与转场管理模块)
   - [5.11 贴纸与装饰管理模块](#511-贴纸与装饰管理模块)
   - [5.12 通用工具模块](#512-通用工具模块)
   - [5.13 视频处理工具模块](#513-视频处理工具模块)
   - [5.14 音频处理工具模块](#514-音频处理工具模块)
   - [5.15 图像处理工具模块](#515-图像处理工具模块)
6. [模块间协作关系](#6-模块间协作关系)
7. [数据流与调用链](#7-数据流与调用链)
8. [分步开发指南](#8-分步开发指南)
9. [最佳实践与注意事项](#9-最佳实践与注意事项)

---

## 1. 项目概述

### 1.1 产品定位

CapCutAPI-Complete 是一个**基于 Python 的视频编辑 API 服务**，它通过 HTTP REST API 和 MCP（Model Context Protocol）两种协议，对外提供程序化的视频编辑能力。用户可以通过 API 调用来完成以下操作：

- 创建视频编辑项目（草稿）
- 添加视频片段到时间轴
- 添加音频轨道（背景音乐、音效、旁白）
- 添加文字和字幕
- 添加特效、转场、滤镜
- 添加贴纸和装饰元素
- 导出最终视频

### 1.2 核心设计理念

项目采用**分层架构**设计：

```
┌─────────────────────────────────────────┐
│           外部调用层                      │
│  HTTP API (REST)  │  MCP Protocol       │
├─────────────────────────────────────────┤
│           服务层                          │
│  capcut_server.py  │  mcp_server.py     │
├─────────────────────────────────────────┤
│           业务逻辑层                       │
│  create_draft / add_video / add_audio   │
│  add_text / add_effects / add_stickers  │
├─────────────────────────────────────────┤
│           工具层                          │
│  video_utils / audio_utils / image_utils│
│  utils (通用工具)                         │
├─────────────────────────────────────────┤
│           核心库层                         │
│  pyJianYingDraft (草稿数据结构)           │
├─────────────────────────────────────────┤
│           存储层                          │
│  JSON 草稿文件 (文件系统)                  │
└─────────────────────────────────────────┘
```

### 1.3 两种服务协议的区别

| 特性 | HTTP API (`capcut_server.py`) | MCP Server (`mcp_server.py`) |
|------|-------------------------------|------------------------------|
| 协议 | HTTP REST (Flask) | MCP (Model Context Protocol) |
| 端口 | 5000 | 5001 |
| 目标用户 | 通用 HTTP 客户端、curl、Postman | AI Agent（如 Claude、GPT） |
| 调用方式 | HTTP POST/GET 请求 | MCP Tool 调用 |
| 参数传递 | JSON Body | 结构化 Schema |

---

## 2. 技术栈与依赖

### 2.1 编程语言

- **Python 3.8+**（推荐 3.11）

### 2.2 核心依赖（`requirements.txt`）

| 类别 | 库名 | 版本 | 用途 |
|------|------|------|------|
| **Web 框架** | Flask | 2.3.3 | HTTP API 服务器 |
| | Flask-CORS | 4.0.0 | 跨域支持 |
| | Flask-RESTful | 0.3.10 | RESTful API 扩展 |
| **HTTP 客户端** | requests | 2.31.0 | 下载远程媒体文件 |
| | httpx | 0.25.2 | 异步 HTTP 请求 |
| **视频处理** | opencv-python | 4.8.1.78 | 视频信息读取 |
| | moviepy | 1.0.3 | 视频编辑 |
| | ffmpeg-python | 0.2.0 | FFmpeg Python 绑定 |
| **音频处理** | pydub | 0.25.1 | 音频文件操作 |
| | librosa | 0.10.1 | 音频分析处理 |
| | soundfile | 0.12.1 | 音频文件读写 |
| **图像处理** | Pillow | 10.0.1 | 图像处理 |
| | numpy | 1.24.3 | 数值计算 |
| | scipy | 1.11.4 | 科学计算 |
| **数据处理** | pandas | 2.0.3 | 数据处理 |
| **缓存/队列** | redis | 5.0.1 | 缓存服务 |
| | celery | 5.3.4 | 异步任务队列 |
| **日志** | loguru | 0.7.2 | 日志管理 |
| **配置** | pyyaml | 6.0.1 | YAML 配置解析 |

### 2.3 MCP 协议依赖（`requirements-mcp.txt`）

| 库名 | 版本 | 用途 |
|------|------|------|
| mcp | 1.0.0 | MCP 协议核心库 |
| websockets | 12.0 | WebSocket 支持 |
| jsonrpc-async | 3.1.0 | JSON-RPC 异步支持 |
| fastapi | 0.104.1 | 异步 Web 框架 |
| uvicorn | 0.24.0 | ASGI 服务器 |
| pydantic | 2.5.0 | 数据验证 |

### 2.4 系统依赖

- **FFmpeg**：视频/音频编解码核心工具，必须安装
- **操作系统**：Windows 10+ / macOS 10.14+ / Ubuntu 18.04+

---

## 3. 项目完整结构

```
CapCutAPI-Complete/
│
├── capcut_server.py          # 【入口】HTTP API 服务器（Flask）
├── mcp_server.py             # 【入口】MCP 协议服务器
│
├── create_draft.py           # 草稿创建与管理
├── add_video_track.py        # 视频轨道管理
├── add_audio_track.py        # 音频轨道管理
├── add_text.py               # 文字与字幕管理
├── add_effects.py            # 特效与转场管理
├── add_stickers.py           # 贴纸与装饰管理
│
├── video_utils.py            # 视频处理工具类
├── audio_utils.py            # 音频处理工具类
├── image_utils.py            # 图像处理工具类
├── utils.py                  # 通用工具函数集
│
├── pyJianYingDraft/          # 核心草稿库
│   └── __init__.py           # 库入口与导出
│
├── requirements.txt          # 核心 Python 依赖
├── requirements-mcp.txt      # MCP 协议额外依赖
│
├── Dockerfile                # Docker 镜像构建
├── docker-compose.yml        # 多服务编排
│
└── README.md                 # 项目说明文档
```

---

## 4. 核心架构设计

### 4.1 草稿（Draft）数据模型

整个系统的核心是一个 **JSON 格式的草稿文件**（`draft.json`），它存储了视频编辑项目的所有信息。草稿的数据结构如下：

```json
{
  "canvas_config": {
    "width": 1080,
    "height": 1920,
    "fps": 30
  },
  "materials": {
    "videos": [],
    "audios": [],
    "images": [],
    "texts": [],
    "effects": [],
    "stickers": []
  },
  "tracks": {
    "video": [],
    "audio": [],
    "text": [],
    "effect": [],
    "sticker": []
  }
}
```

**关键概念**：
- **Material（素材）**：原始媒体文件（视频、音频、图片等）的元数据描述
- **Track（轨道）**：时间轴上的一个层，同一轨道内的片段按时间排列
- **Segment（片段）**：轨道上的一个时间片段，引用一个素材并指定其在时间轴上的位置
- **Effect（效果）**：附加在片段上的视觉或音频效果

### 4.2 草稿文件存储

草稿存储在用户主目录下的 `CapCutDrafts/` 文件夹中：

```
~/CapCutDrafts/
└── {draft_id}/
    ├── draft.json          # 草稿主文件
    ├── videos/             # 下载的视频文件
    ├── audios/             # 下载的音频文件
    ├── images/             # 下载的图片文件
    ├── texts/              # 文本配置
    ├── effects/            # 特效配置
    ├── stickers/           # 贴纸文件
    └── subtitles/          # 字幕文件
```

---

## 5. 文件逐一详解

### 5.1 依赖配置文件

#### `requirements.txt`

**功能**：定义项目运行所需的所有 Python 第三方库。

**关键依赖分组**：
- Flask 系列：提供 HTTP API 服务能力
- opencv-python / moviepy / ffmpeg-python：视频处理核心
- pydub / librosa / soundfile：音频处理核心
- Pillow / numpy：图像处理核心
- redis / celery：缓存和异步任务（可选，用于生产环境）

**开发时的安装命令**：
```bash
pip install -r requirements.txt
```

---

#### `requirements-mcp.txt`

**功能**：定义 MCP 协议服务器所需的额外依赖。

**关键依赖**：
- `mcp`：MCP 协议的核心实现库
- `fastapi` + `uvicorn`：MCP 服务器使用的异步 Web 框架
- `pydantic`：用于定义工具输入参数的 Schema 验证

**开发时的安装命令**：
```bash
pip install -r requirements-mcp.txt
```

---

### 5.2 Docker 部署文件

#### `Dockerfile`

**功能**：定义 Docker 镜像的构建步骤，用于容器化部署。

**构建步骤**：
1. 基于 `python:3.11-slim` 轻量镜像
2. 安装系统依赖（ffmpeg、curl、git）
3. 复制并安装 Python 依赖
4. 复制应用代码
5. 创建运行时目录（downloads、uploads、temp）
6. 暴露 5000 端口
7. 配置健康检查
8. 启动 Flask 应用

**关键配置**：
- `EXPOSE 5000`：HTTP API 端口
- `HEALTHCHECK`：每 30 秒检查 `/health` 端点
- `FLASK_ENV=production`：生产模式运行

---

#### `docker-compose.yml`

**功能**：编排多个 Docker 服务，实现完整的生产环境部署。

**定义的服务**：

| 服务名 | 镜像 | 端口 | 用途 |
|--------|------|------|------|
| `capcut-api` | 本地构建 | 5000 | HTTP API 主服务 |
| `nginx` | nginx:alpine | 80/443 | 反向代理与 SSL 终端 |
| `redis` | redis:alpine | 6379 | 缓存服务 |
| `mcp-server` | 本地构建 | 5001 | MCP 协议服务 |

**数据卷挂载**：
- `./downloads:/app/downloads`：下载文件持久化
- `./uploads:/app/uploads`：上传文件持久化
- `./temp:/app/temp`：临时文件
- `redis_data`：Redis 数据持久化

---

### 5.3 核心库 pyJianYingDraft

#### `pyJianYingDraft/__init__.py`

**功能**：这是整个项目的核心库入口文件。它定义了草稿（Draft）的数据结构和操作接口。

**导出的核心类**：
- `Draft`：草稿对象，代表一个完整的视频编辑项目
- `Track`：轨道对象，代表时间轴上的一个层
- `Segment`：片段基类
- `VideoSegment`：视频片段
- `AudioSegment`：音频片段
- `ImageSegment`：图片片段
- `TextSegment`：文字片段
- `Effect`：效果基类
- `TransitionEffect`：转场效果
- `FilterEffect`：滤镜效果
- `TextStyle`：文字样式
- `TextAnimation`：文字动画

**导出的工具函数**：
- `generate_uuid()`：生成唯一 ID
- `validate_color()`：验证颜色格式
- `format_duration()`：格式化时长
- `parse_duration()`：解析时长字符串
- `convert_to_capcut_format()`：转换为剪映格式

**导出的常量**：
- `DEFAULT_WIDTH` / `DEFAULT_HEIGHT`：默认画布尺寸（1080x1920）
- `DEFAULT_FPS`：默认帧率（30）
- `VIDEO_CODECS` / `AUDIO_CODECS`：支持的编解码器列表
- `SUPPORTED_FORMATS`：支持的媒体格式
- `EFFECT_TYPES` / `TRANSITION_TYPES` / `ANIMATION_TYPES`：效果类型枚举

**初始化行为**：
- 自动创建 `~/.capcut_drafts/`（草稿存储目录）
- 自动创建 `~/.capcut_temp/`（临时文件目录）
- 自动创建 `~/.capcut_cache/`（缓存目录）
- 检测可选依赖（Pillow、NumPy）的可用性

---

### 5.4 HTTP API 服务器

#### `capcut_server.py`

**功能**：基于 Flask 框架的 HTTP REST API 服务器，是整个项目的主要对外接口。

**导入的关键模块**：
```python
from flask import Flask, request, jsonify
import pyJianYingDraft as draft
from pyJianYingDraft.metadata.animation_meta import Intro_type, Outro_type, ...
from pyJianYingDraft.metadata.transition_meta import Transition_type
from pyJianYingDraft.metadata.mask_meta import Mask_type
from pyJianYingDraft.metadata.font_meta import Font_type
# ... 更多元数据导入
```

**提供的 API 端点**：

| 端点 | 方法 | 功能 | 关键参数 |
|------|------|------|----------|
| `/create_draft` | POST | 创建新草稿 | `draft_name`, `width`, `height`, `fps` |
| `/add_video` | POST | 添加视频片段 | `video_url`, `start`, `end`, `speed`, `transition`, `mask_type`, `volume` |
| `/add_audio` | POST | 添加音频片段 | `audio_url`, `start`, `end`, `volume`, `speed`, `effect_type` |
| `/add_text` | POST | 添加文字 | `text`, `font_size`, `color`, `start`, `duration`, `x`, `y`, `text_intro`, `text_outro` |
| `/add_subtitle` | POST | 添加字幕 | `text`, `font_size`, `color`, `start`, `duration`, `max_width`, `line_spacing` |
| `/add_image` | POST | 添加图片 | `image_url`, `start`, `duration`, `x`, `y`, `scale_x`, `scale_y`, `rotation` |
| `/add_effect` | POST | 添加特效 | `effect_type`, `effect_name`, `start`, `duration`, `intensity` |
| `/add_sticker` | POST | 添加贴纸 | `sticker_url`, `start`, `duration`, `x`, `y`, `scale_x`, `scale_y`, `rotation` |
| `/save_draft` | POST | 保存并导出草稿 | `draft_id` |
| `/query_task` | POST | 查询导出任务状态 | `draft_id` |
| `/query_script` | POST | 查询脚本信息 | `draft_id` |
| `/add_video_keyframe` | POST | 添加视频关键帧 | `start`, `duration`, `x`, `y`, `scale_x`, `scale_y`, `rotation`, `opacity` |
| `/generate_draft_url` | POST | 生成草稿访问 URL | `draft_id` |
| `/health` | GET | 健康检查 | 无 |

**统一的响应格式**：
```json
{
  "success": true/false,
  "output": "...",    // 成功时的返回数据
  "error": "..."      // 失败时的错误信息
}
```

**参数处理模式**（以 `/add_video` 为例）：
1. 从 `request.get_json()` 获取请求体
2. 使用 `data.get('key', default_value)` 提取每个参数
3. 验证必填参数（如 `video_url`）
4. 调用对应的业务逻辑函数（如 `add_video_track()`）
5. 捕获异常并返回错误信息

**启动方式**：
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
```

---

### 5.5 MCP 协议服务器

#### `mcp_server.py`

**功能**：基于 MCP（Model Context Protocol）协议的工具服务器，专门用于 AI Agent（如 Claude Desktop）集成。

**核心类 `CapCutMCPServer`**：
- `__init__()`：初始化服务器，维护 `self.drafts` 字典追踪草稿状态
- `get_tools()`：返回可用工具列表（包含每个工具的 name、description、inputSchema）
- `call_tool(name, arguments)`：根据工具名称路由到对应的处理方法

**定义的 MCP 工具**（共 9 个）：

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `create_draft` | 创建新草稿 | 无（width/height 可选） |
| `add_video` | 添加视频 | `video_url` |
| `add_audio` | 添加音频 | `audio_url` |
| `add_image` | 添加图片 | `image_url` |
| `add_text` | 添加文字 | `text`, `start`, `end` |
| `add_subtitle` | 添加字幕 | `srt_path` |
| `add_effect` | 添加特效 | `effect_type` |
| `add_sticker` | 添加贴纸 | `sticker_url` |
| `save_draft` | 保存草稿 | `draft_id` |

**与 HTTP API 的关键区别**：
- MCP 服务器内部维护草稿状态（`self.drafts`），不需要客户端传递 `draft_folder`
- 每个工具的 `inputSchema` 使用 JSON Schema 格式定义参数类型和默认值
- 工具描述中包含中文说明，方便 AI Agent 理解

**启动方式**（使用 MCP stdio 传输）：
```python
asyncio.run(mcp.server.stdio.run(
    handle_call_tool,
    handle_list_tools,
    InitializationOptions(
        server_name="capcut-api",
        server_version="1.0.0",
    ),
))
```

---

### 5.6 草稿管理模块

#### `create_draft.py`

**功能**：提供草稿的创建、查询、删除等管理功能。

**核心函数**：

1. **`get_or_create_draft(draft_id, width, height)`**
   - 在 `~/CapCutDrafts/{draft_id}/` 创建草稿文件夹
   - 自动创建 7 个子目录：`videos/`, `audios/`, `images/`, `texts/`, `effects/`, `stickers/`, `subtitles/`
   - 返回草稿文件夹的绝对路径

2. **`list_drafts()`**
   - 扫描 `~/CapCutDrafts/` 下所有草稿
   - 返回每个草稿的 ID、路径、创建时间、修改时间、大小
   - 按修改时间倒序排列

3. **`delete_draft(draft_id)`**
   - 使用 `shutil.rmtree()` 递归删除整个草稿文件夹

4. **`get_draft_info(draft_id)`**
   - 统计草稿中各类型文件的数量
   - 返回详细的文件统计信息

**设计要点**：
- 草稿 ID 使用 UUID 生成，确保唯一性
- 每个草稿是独立的文件夹，便于管理和迁移
- 子目录按媒体类型分类，结构清晰

---

### 5.7 视频轨道管理模块

#### `add_video_track.py`

**功能**：管理视频片段的添加、删除、更新操作。

**核心函数 `add_video_track()`**：

**参数列表**（共 20+ 个参数）：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `draft_folder` | str | 必填 | 草稿文件夹路径 |
| `video_url` | str | 必填 | 视频 URL 或本地路径 |
| `start` | float | 0 | 裁剪开始时间（秒） |
| `end` | float | None | 裁剪结束时间（秒） |
| `target_start` | float | 0 | 时间轴上的起始位置 |
| `width` | int | 1080 | 画布宽度 |
| `height` | int | 1920 | 画布高度 |
| `transform_x/y` | float | 0 | 位置偏移 |
| `scale_x/y` | float | 1 | 缩放比例 |
| `speed` | float | 1.0 | 播放速度 |
| `volume` | float | 1.0 | 音量 |
| `transition` | str | None | 转场类型 |
| `transition_duration` | float | 0.5 | 转场时长 |
| `mask_type` | str | None | 蒙版类型 |
| `background_blur` | int | None | 背景模糊级别(1-4) |

**处理流程**：
1. 验证草稿文件夹存在
2. 加载或创建 `draft.json`
3. 如果 `video_url` 是 HTTP URL，使用 `requests` 下载到 `videos/` 目录
4. 使用 OpenCV (`cv2`) 读取视频信息（时长、帧率）
5. 生成唯一的 `material_id` 和 `segment_id`
6. 创建视频素材（material）和视频片段（segment）数据结构
7. 如果指定了转场/蒙版/背景模糊，创建对应的效果对象
8. 查找或创建指定名称的视频轨道
9. 将片段添加到轨道中
10. 保存 `draft.json`

**辅助函数**：
- `remove_video_track(draft_folder, segment_id)`：移除指定视频片段
- `update_video_track(draft_folder, segment_id, **kwargs)`：更新视频片段参数

---

### 5.8 音频轨道管理模块

#### `add_audio_track.py`

**功能**：管理音频片段的添加、删除、更新操作。

**核心函数 `add_audio_track()`**：

**关键参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `audio_url` | str | 必填 | 音频 URL 或本地路径 |
| `volume` | float | 1.0 | 音量（0-2） |
| `speed` | float | 1.0 | 播放速度（0.5-2.0） |
| `fade_in` | float | 0 | 淡入时长（秒） |
| `fade_out` | float | 0 | 淡出时长（秒） |
| `audio_type` | str | "music" | 音频类型（music/sound_effect/voice_over） |
| `normalize` | bool | True | 是否标准化音量 |
| `loop` | bool | False | 是否循环播放 |

**处理流程**：
1. 验证草稿文件夹存在
2. 加载或创建 `draft.json`
3. 如果 `audio_url` 是 HTTP URL，下载到 `audios/` 目录
4. 使用 `pydub` 读取音频时长
5. 生成唯一 ID，创建音频素材和片段
6. 查找或创建音频轨道，添加片段
7. 保存 `draft.json`

**便捷函数**：
- `add_sound_effect(draft_folder, effect_url, ...)`：添加音效（`audio_type="sound_effect"`）
- `add_voice_over(draft_folder, voice_url, ...)`：添加旁白（`audio_type="voice_over"`）
- `adjust_audio_levels(draft_folder, track_name, volume)`：调整整个轨道的音量

---

### 5.9 文字与字幕管理模块

#### `add_text.py`

**功能**：管理文字、字幕、标题的添加、删除、更新操作。

**核心函数 `add_text()`**：

**关键参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | str | 必填 | 文字内容 |
| `start` | float | 0 | 开始时间（秒） |
| `duration` | float | 5 | 持续时间（秒） |
| `x`, `y` | float | 540, 960 | 坐标位置（像素） |
| `font_size` | int | 32 | 字体大小 |
| `font_family` | str | "PingFang SC" | 字体族 |
| `color` | str | "#FFFFFF" | 文字颜色 |
| `background_color` | str | None | 背景颜色 |
| `stroke_color` | str | None | 描边颜色 |
| `stroke_width` | int | 0 | 描边宽度 |
| `shadow_color` | str | None | 阴影颜色 |
| `opacity` | float | 1.0 | 透明度 |
| `rotation` | float | 0 | 旋转角度 |
| `alignment` | str | "center" | 对齐方式（left/center/right） |
| `line_spacing` | float | 1.2 | 行间距 |
| `letter_spacing` | float | 0 | 字间距 |
| `animation_type` | str | None | 动画类型 |
| `animation_duration` | float | 1.0 | 动画时长 |

**便捷函数**：
- `add_subtitle(draft_folder, text, start, end, ...)`：添加单条字幕（自动计算 duration = end - start，默认位置在底部 y=1700）
- `add_title(draft_folder, title, subtitle, ...)`：添加标题（支持主标题+副标题，副标题自动偏移 60px）
- `add_subtitle_track(draft_folder, subtitles, ...)`：批量添加字幕轨道

**辅助函数**：
- `remove_text(draft_folder, segment_id)`：移除文字片段
- `update_text(draft_folder, segment_id, **kwargs)`：更新文字参数

---

### 5.10 特效与转场管理模块

#### `add_effects.py`

**功能**：管理各种视觉效果的添加。

**定义的特效类型枚举 `EFFECT_TYPES`**：
```python
EFFECT_TYPES = {
    "transition": ["fade", "slide", "wipe", "zoom", "dissolve", "push", "cover"],
    "filter": ["vintage", "black_white", "sepia", "cold", "warm", "sharpen", "blur"],
    "adjust": ["brightness", "contrast", "saturation", "hue", "exposure", "gamma"],
    "animation": ["scale", "rotate", "position", "opacity"],
    "mask": ["circle", "rectangle", "heart", "star", "custom"],
    "particle": ["snow", "rain", "fireworks", "sparkle", "bubbles"],
    "distortion": ["wave", "ripple", "twirl", "bulge"]
}
```

**核心函数**：

1. **`add_transition(draft_folder, transition_type, duration, target_segment_id, position, easing)`**
   - 添加转场效果（fade/slide/wipe 等）
   - 支持指定目标片段和转场位置（start/end/between）
   - 效果存入 `"transitions"` 轨道

2. **`add_filter(draft_folder, filter_type, intensity, target_segment_id, start, duration)`**
   - 添加滤镜效果（vintage/sepia/blur 等）
   - `intensity` 控制滤镜强度（0-1）
   - 效果存入 `"filters"` 轨道

3. **`add_adjustment(draft_folder, adjustment_type, value, target_segment_id, start, duration)`**
   - 添加画面调整（brightness/contrast/saturation 等）
   - 效果存入 `"adjustments"` 轨道

4. **`add_animation(draft_folder, animation_type, start_value, end_value, target_segment_id, start, duration, easing)`**
   - 添加关键帧动画（scale/rotate/position/opacity）
   - 支持缓动函数（ease_in_out 等）
   - 效果存入 `"animations"` 轨道

---

### 5.11 贴纸与装饰管理模块

#### `add_stickers.py`

**功能**：管理贴纸、表情符号、文字气泡等装饰元素。

**核心类 `StickerManager`**：

**主要方法**：
| 方法 | 功能 |
|------|------|
| `add_sticker(sticker_type, position, size, rotation, opacity, start, duration, animation, ...)` | 添加通用贴纸 |
| `add_emoji(emoji, **kwargs)` | 添加表情符号 |
| `add_text_bubble(text, bubble_type, position, font_size, **kwargs)` | 添加文字气泡 |
| `add_custom_sticker(file_path, sticker_name, **kwargs)` | 添加自定义贴纸（从文件） |
| `add_animated_sticker(sticker_type, animation_type, **kwargs)` | 添加带动画的贴纸 |
| `move_sticker(sticker_id, new_position)` | 移动贴纸位置 |
| `resize_sticker(sticker_id, new_size)` | 调整贴纸大小 |
| `remove_sticker(sticker_id)` | 移除贴纸 |
| `list_stickers()` | 列出所有贴纸 |

**贴纸类型定义 `STICKER_TYPES`**：
```python
STICKER_TYPES = {
    "emoji": ["smile", "heart", "thumbs_up", "fire", "star", ...],
    "decoration": ["border", "frame", "overlay", "light_leak", "bokeh", "glitter"],
    "text_bubble": ["speech", "thought", "shout", "whisper"],
    "animated": ["gif", "lottie", "animated_emoji"],
    "custom": ["upload", "url", "local"]
}
```

**便捷函数**（模块级别）：
- `add_sticker_to_draft(draft_folder, sticker_type, **kwargs)`
- `add_emoji_to_draft(draft_folder, emoji, **kwargs)`
- `add_text_bubble_to_draft(draft_folder, text, **kwargs)`

---

### 5.12 通用工具模块

#### `utils.py`

**功能**：提供项目中通用的工具函数，按功能组织为多个工具类。

**包含的工具类**：

1. **`FileUtils`** — 文件操作
   - `ensure_dir(directory)`：确保目录存在
   - `get_file_hash(file_path, algorithm)`：计算文件哈希
   - `get_file_info(file_path)`：获取文件详细信息
   - `safe_move(src, dst)` / `safe_copy(src, dst)`：安全移动/复制
   - `delete_file(file_path)`：删除文件
   - `list_files(directory, pattern, recursive, extensions)`：列出文件
   - `create_temp_dir(prefix)` / `create_temp_file(suffix, prefix)`：创建临时目录/文件
   - `extract_archive(archive_path, extract_to)`：解压归档文件
   - `create_archive(files, archive_path, format)`：创建归档文件

2. **`URLUtils`** — URL 处理
   - `is_valid_url(url)`：验证 URL 有效性
   - `get_filename_from_url(url)`：从 URL 提取文件名
   - `download_file(url, output_path, timeout, max_retries)`：下载文件（支持重试和指数退避）
   - `get_url_info(url)`：获取 URL 信息（HEAD 请求）

3. **`StringUtils`** — 字符串处理
   - `sanitize_filename(filename)`：清理文件名中的非法字符
   - `truncate_text(text, max_length, suffix)`：截断文本
   - `extract_numbers(text)`：从文本提取数字
   - `is_json_string(text)`：检查是否为 JSON 字符串
   - `format_duration(seconds)`：格式化时长（如 "2.5m"）
   - `format_file_size(size_bytes)`：格式化文件大小（如 "1.5 MB"）

4. **`TimeUtils`** — 时间处理
   - `get_timestamp()`：获取当前时间戳
   - `format_timestamp(timestamp, format)`：格式化时间戳
   - `parse_duration(duration_str)`：解析时长字符串（支持 "1h30m"、"90m"、"3600s" 等格式）
   - `get_time_ago(timestamp)`：获取相对时间描述

5. **`ValidationUtils`** — 验证工具
   - `is_valid_email(email)`：验证邮箱
   - `is_valid_url(url)`：验证 URL
   - `is_valid_hex_color(color)`：验证十六进制颜色
   - `is_valid_video_file(file_path)`：验证视频文件扩展名
   - `is_valid_audio_file(file_path)`：验证音频文件扩展名
   - `is_valid_image_file(file_path)`：验证图片文件扩展名

6. **`CacheUtils`** — 缓存工具
   - `set(key, data, expire_hours)`：设置缓存（JSON 文件存储）
   - `get(key)`：获取缓存（自动检查过期）

---

### 5.13 视频处理工具模块

#### `video_utils.py`

**功能**：提供底层的视频处理能力，基于 FFmpeg 命令行工具。

**核心类 `VideoProcessor`**：

**属性**：
- `supported_formats`：支持的视频格式列表
- `common_resolutions`：常用分辨率映射（720p/1080p/4K 等）
- `common_fps`：常用帧率列表

**核心方法**：

| 方法 | 功能 | 关键技术 |
|------|------|----------|
| `get_video_info(video_file)` | 获取视频信息 | `ffprobe` 命令，解析 JSON 输出 |
| `convert_video_format(input, output, format, codec, quality, preset)` | 转换视频格式 | `ffmpeg` + libx264 编码器 |
| `resize_video(input, output, width, height, keep_aspect, interpolation)` | 调整分辨率 | `ffmpeg` scale 滤镜，支持 lanczos 插值 |
| `change_fps(input, output, target_fps, method)` | 改变帧率 | 简单 fps 转换或 minterpolate 插值 |
| `trim_video(input, output, start_time, duration, accurate)` | 裁剪视频 | 精确模式（重编码）或快速模式（copy） |
| `merge_videos(input_files, output, transition, transition_duration)` | 合并视频 | concat 协议，支持转场 |
| `extract_frames(input, output_dir, fps, quality)` | 提取视频帧 | `ffmpeg` 帧提取为 JPG |
| `add_watermark(input, output, watermark_file, position, opacity, scale)` | 添加水印 | overlay 滤镜 |
| `add_text_overlay(input, output, text, position, font_size, font_color, ...)` | 添加文字覆盖 | drawtext 滤镜 |
| `create_thumbnail(input, output, time, width, height)` | 创建缩略图 | 截取单帧 + scale |

**设计模式**：
- 所有方法返回统一的 `{"success": True/False, ...}` 字典格式
- 使用 `subprocess.run()` 调用 FFmpeg 命令行
- 捕获 `stderr` 作为错误信息

---

### 5.14 音频处理工具模块

#### `audio_utils.py`

**功能**：提供底层的音频处理能力，结合 FFmpeg 和 librosa 库。

**核心类 `AudioProcessor`**：

**核心方法**：

| 方法 | 功能 | 关键技术 |
|------|------|----------|
| `convert_audio_format(input, output, format, sample_rate, bitrate, channels)` | 转换音频格式 | `ffmpeg` 音频转码 |
| `adjust_volume(input, output, volume_change, normalize)` | 调整音量 | `librosa` 加载 → 数值运算 → `soundfile` 保存 |
| `extract_audio_from_video(video_file, output, format, quality)` | 从视频提取音频 | `ffmpeg -vn` 禁用视频流 |
| `trim_audio(input, output, start_time, duration)` | 裁剪音频 | `ffmpeg -ss -t` |
| `fade_in_out(input, output, fade_in, fade_out)` | 淡入淡出 | `ffmpeg afade` 音频滤镜 |
| `add_background_music(main_audio, bg_audio, output, bg_volume, loop)` | 添加背景音乐 | `ffmpeg amix` 音频混合滤镜 |
| `normalize_audio(input, output, target_lufs)` | 标准化音量 | `ffmpeg loudnorm` 响度标准化 |
| `get_audio_info(audio_file)` | 获取音频信息 | `ffprobe` 命令 |
| `detect_silence(audio_file, threshold, min_duration)` | 检测静音段 | `librosa` RMS 能量分析 |

---

### 5.15 图像处理工具模块

#### `image_utils.py`

**功能**：提供底层的图像处理能力，基于 Pillow 和 OpenCV。

**核心类 `ImageProcessor`**：

**核心方法**：

| 方法 | 功能 | 关键技术 |
|------|------|----------|
| `get_image_info(image_file)` | 获取图片信息 | Pillow `Image.open()`，读取 EXIF |
| `convert_format(input, output, format, quality)` | 转换图片格式 | Pillow 格式转换（JPEG/PNG/WebP） |
| `resize_image(input, output, width, height, keep_aspect, resample, bg_color)` | 调整尺寸 | Pillow `resize()`，支持保持宽高比和背景填充 |
| `crop_image(input, output, left, top, right, bottom)` | 裁剪图片 | Pillow `crop()` |
| `rotate_image(input, output, angle, expand, fillcolor)` | 旋转图片 | Pillow `rotate()` |
| `apply_filter(input, output, filter_type, **kwargs)` | 应用滤镜 | Pillow `ImageFilter` + `ImageEnhance`（模糊/锐化/灰度/复古/亮度/对比度/饱和度） |
| `add_text(input, output, text, position, font_size, font_color, ...)` | 添加文字 | Pillow `ImageDraw.text()`，支持描边和背景 |
| `add_watermark(input, output, watermark_file, position, opacity, scale, margin)` | 添加水印 | Pillow 图层叠加，支持透明度 |
| `create_collage(input_files, output, layout, cols, spacing, ...)` | 创建拼贴 | Pillow 多图拼接（grid/horizontal/vertical） |
| `create_meme(input, output, top_text, bottom_text, ...)` | 创建表情包 | Pillow 图片+上下文字边框 |

**辅助方法**：
- `_fix_orientation(img)`：根据 EXIF 方向信息自动旋转图片
- `_apply_sepia(img)`：应用复古棕褐色滤镜
- `_apply_vintage(img)`：应用怀旧滤镜

---

## 6. 模块间协作关系

### 6.1 依赖关系图

```
capcut_server.py (HTTP API)
    ├── 导入 → create_draft.py
    ├── 导入 → add_video_track.py
    ├── 导入 → add_audio_track.py
    ├── 导入 → add_text_impl (外部实现)
    ├── 导入 → add_effect_impl (外部实现)
    ├── 导入 → add_sticker_impl (外部实现)
    ├── 导入 → save_draft_impl (外部实现)
    ├── 导入 → util.py (generate_draft_url, hex_to_rgb)
    ├── 导入 → settings.local (配置)
    └── 导入 → pyJianYingDraft (核心库)

mcp_server.py (MCP Protocol)
    ├── 导入 → create_draft.py
    ├── 导入 → add_video_track.py
    ├── 导入 → add_audio_track.py
    ├── 导入 → add_text_impl (外部实现)
    ├── 导入 → add_image_impl (外部实现)
    ├── 导入 → add_subtitle_impl (外部实现)
    ├── 导入 → add_effect_impl (外部实现)
    ├── 导入 → add_sticker_impl (外部实现)
    ├── 导入 → save_draft_impl (外部实现)
    └── 导入 → pyJianYingDraft (核心库)

业务模块 (add_*.py)
    ├── 导入 → pyJianYingDraft (数据结构)
    └── 使用 → json (读写 draft.json)

工具模块 (video_utils/audio_utils/image_utils/utils.py)
    └── 独立工具类，被业务模块按需调用
```

### 6.2 典型调用链

以"用户通过 HTTP API 创建一个带文字的视频"为例：

```
1. POST /create_draft
   → capcut_server.py: create_draft_service()
   → create_draft.py: get_or_create_draft()
   → 在文件系统创建 ~/CapCutDrafts/{draft_id}/

2. POST /add_video
   → capcut_server.py: add_video()
   → add_video_track.py: add_video_track()
   → 下载视频文件到 videos/ 目录
   → 读取/创建 draft.json
   → 添加 video material 和 segment 到 draft.json

3. POST /add_text
   → capcut_server.py: add_text()
   → add_text_impl (外部实现)
   → 读取 draft.json
   → 添加 text material 和 segment 到 draft.json

4. POST /save_draft
   → capcut_server.py: save_draft()
   → save_draft_impl (外部实现)
   → 读取 draft.json，生成最终视频
```

---

## 7. 数据流与调用链

### 7.1 草稿 JSON 的完整生命周期

```
[创建] → create_draft.py
   ↓
[空 draft.json] → {"canvas_config": {...}, "materials": {...}, "tracks": {...}}
   ↓
[添加视频] → add_video_track.py
   ↓ 在 materials.videos 中添加素材
   ↓ 在 tracks.video 中添加片段
   ↓
[添加音频] → add_audio_track.py
   ↓ 在 materials.audios 中添加素材
   ↓ 在 tracks.audio 中添加片段
   ↓
[添加文字] → add_text.py
   ↓ 在 materials.texts 中添加素材
   ↓ 在 tracks.text 中添加片段
   ↓
[添加特效] → add_effects.py
   ↓ 在 materials.effects 中添加效果
   ↓ 在 tracks.effect 中添加效果片段
   ↓
[保存/导出] → save_draft_impl
   ↓ 读取完整的 draft.json
   ↓ 调用 FFmpeg 渲染最终视频
```

### 7.2 轨道（Track）的工作机制

每个轨道是一个独立的层，同一轨道内的片段按 `target_start` 时间排序：

```
时间轴 →
Track "video_main":
  [Segment A: 0s-5s] [Segment B: 5s-10s]

Track "audio_main":
  [Segment C: 0s-10s]  (背景音乐)

Track "text_main":
  [Segment D: 2s-7s]   (标题文字)

Track "subtitles":
  [Segment E: 0s-3s] [Segment F: 3s-6s] [Segment G: 6s-10s]
```

---

## 8. 分步开发指南

以下是引导用户从零开始开发这个产品的步骤：

### 第 1 步：环境准备

1. 安装 Python 3.11+
2. 安装 FFmpeg 并确保在系统 PATH 中
3. 创建项目文件夹 `CapCutAPI-Complete/`
4. 创建 Python 虚拟环境

```bash
mkdir CapCutAPI-Complete
cd CapCutAPI-Complete
python -m venv venv
venv\Scripts\activate  # Windows
# 或 source venv/bin/activate  # macOS/Linux
```

### 第 2 步：创建依赖文件

1. 创建 `requirements.txt`，内容参考本文档第 5.1 节
2. 创建 `requirements-mcp.txt`，内容参考本文档第 5.1 节
3. 安装依赖：`pip install -r requirements.txt`

### 第 3 步：创建核心库 pyJianYingDraft

1. 创建 `pyJianYingDraft/` 文件夹
2. 创建 `pyJianYingDraft/__init__.py`
3. 实现 `Draft`、`Track`、`Segment` 等核心类
4. 实现 `generate_uuid()`、`validate_color()` 等工具函数
5. 定义常量（分辨率、帧率、编解码器等）

### 第 4 步：创建通用工具模块

1. 创建 `utils.py`，实现 `FileUtils`、`URLUtils`、`StringUtils`、`TimeUtils`、`ValidationUtils`、`CacheUtils` 六个工具类
2. 创建 `video_utils.py`，实现 `VideoProcessor` 类（基于 FFmpeg）
3. 创建 `audio_utils.py`，实现 `AudioProcessor` 类（基于 FFmpeg + librosa）
4. 创建 `image_utils.py`，实现 `ImageProcessor` 类（基于 Pillow）

### 第 5 步：创建草稿管理模块

1. 创建 `create_draft.py`
2. 实现 `get_or_create_draft()` 函数
3. 实现 `list_drafts()`、`delete_draft()`、`get_draft_info()` 辅助函数

### 第 6 步：创建业务逻辑模块

按以下顺序逐个创建：

1. **`add_video_track.py`**：视频轨道管理
   - `add_video_track()` — 核心添加函数
   - `remove_video_track()` — 删除函数
   - `update_video_track()` — 更新函数

2. **`add_audio_track.py`**：音频轨道管理
   - `add_audio_track()` — 核心添加函数
   - `add_sound_effect()` — 音效便捷函数
   - `add_voice_over()` — 旁白便捷函数
   - `adjust_audio_levels()` — 音量调整函数

3. **`add_text.py`**：文字与字幕管理
   - `add_text()` — 核心添加函数
   - `add_subtitle()` — 字幕便捷函数
   - `add_title()` — 标题便捷函数
   - `add_subtitle_track()` — 批量字幕函数

4. **`add_effects.py`**：特效管理
   - `add_transition()` — 转场效果
   - `add_filter()` — 滤镜效果
   - `add_adjustment()` — 画面调整
   - `add_animation()` — 关键帧动画

5. **`add_stickers.py`**：贴纸管理
   - `StickerManager` 类及其所有方法
   - 模块级别的便捷函数

### 第 7 步：创建 HTTP API 服务器

1. 创建 `capcut_server.py`
2. 初始化 Flask 应用
3. 逐个实现 API 端点（参考第 5.4 节的端点列表）
4. 每个端点的实现模式：
   - 解析请求参数
   - 验证必填参数
   - 调用对应的业务逻辑函数
   - 返回统一的 JSON 响应

### 第 8 步：创建 MCP 协议服务器

1. 创建 `mcp_server.py`
2. 定义 `TOOLS` 列表（每个工具的 name、description、inputSchema）
3. 实现 `CapCutMCPServer` 类
4. 实现 MCP stdio 服务器启动逻辑

### 第 9 步：创建 Docker 部署文件

1. 创建 `Dockerfile`
2. 创建 `docker-compose.yml`
3. 测试 Docker 构建和运行

### 第 10 步：测试与验证

1. 启动 HTTP API 服务器：`python capcut_server.py`
2. 使用 curl 测试每个端点
3. 启动 MCP 服务器：`python mcp_server.py`
4. 验证完整的视频编辑流程

---

## 9. 最佳实践与注意事项

### 9.1 代码组织

1. **每个文件只负责一个领域**：视频、音频、文字、特效、贴纸各自独立
2. **统一的响应格式**：所有函数返回 `{"success": True/False, ...}` 字典
3. **统一的 ID 生成**：使用 `generate_uuid()` 确保全局唯一

### 9.2 错误处理

1. **每个函数都用 try-except 包裹**核心逻辑
2. **返回明确的错误信息**：`{"success": False, "error": "具体错误描述"}`
3. **参数验证前置**：在执行业务逻辑前先验证必填参数

### 9.3 草稿文件管理

1. **草稿文件是单一事实来源**：所有操作都读写同一个 `draft.json`
2. **每次操作后立即保存**：避免数据丢失
3. **使用 `ensure_ascii=False, indent=2`** 保存 JSON，保证可读性

### 9.4 媒体文件处理

1. **远程文件先下载到本地**：使用 `requests` 流式下载
2. **按类型分目录存储**：videos/audios/images/stickers/
3. **使用内容 ID 命名文件**：避免文件名冲突

### 9.5 FFmpeg 调用

1. **使用 `subprocess.run()` 而非 `os.system()`**：更好的错误处理
2. **始终捕获 stderr**：FFmpeg 的错误信息在 stderr 中
3. **使用 `-y` 参数**：自动覆盖输出文件，避免交互式确认

### 9.6 性能优化

1. **视频信息获取使用 ffprobe**：比 OpenCV 更快
2. **音频处理优先使用 FFmpeg**：比 librosa 处理大文件更高效
3. **图片处理使用 Pillow**：比 OpenCV 更适合格式转换

### 9.7 安全注意事项

1. **验证 URL 有效性**：防止 SSRF 攻击
2. **限制文件大小**：防止磁盘耗尽
3. **清理临时文件**：定期清理 temp 目录
4. **不要信任用户输入的文件名**：使用 `sanitize_filename()` 清理

### 9.8 扩展性设计

1. **轨道系统支持无限扩展**：通过 `track_name` 参数创建任意数量的轨道
2. **效果系统支持自定义参数**：通过 `parameters` 字典传递额外配置
3. **双协议支持**：HTTP API 和 MCP 协议共享同一套业务逻辑

---

## 附录：关键数据结构参考

### A. Video Material（视频素材）
```json
{
  "id": "uuid",
  "type": "video",
  "name": "文件名.mp4",
  "path": "/path/to/video.mp4",
  "duration": 30.0,
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "volume": 1.0,
  "speed": 1.0
}
```

### B. Video Segment（视频片段）
```json
{
  "id": "uuid",
  "material_id": "uuid",
  "start": 0,
  "duration": 10.0,
  "target_start": 0,
  "target_duration": 10.0,
  "transform": {
    "x": 0, "y": 0,
    "scale_x": 1.0, "scale_y": 1.0
  },
  "effects": []
}
```

### C. Audio Material（音频素材）
```json
{
  "id": "uuid",
  "type": "audio",
  "name": "文件名.mp3",
  "path": "/path/to/audio.mp3",
  "duration": 60.0,
  "audio_type": "music",
  "volume": 0.8,
  "speed": 1.0,
  "fade_in": 0.5,
  "fade_out": 0.5,
  "normalize": true,
  "loop": false
}
```

### D. Text Material（文字素材）
```json
{
  "id": "uuid",
  "type": "text",
  "content": "Hello World",
  "font": {
    "family": "PingFang SC",
    "size": 48,
    "weight": "bold",
    "color": "#FFFFFF"
  },
  "background": {
    "color": "#000000",
    "opacity": 0.7
  },
  "stroke": {
    "color": "#000000",
    "width": 2
  },
  "shadow": {
    "color": "#000000",
    "offset_x": 2,
    "offset_y": 2,
    "blur": 4
  },
  "alignment": "center",
  "line_spacing": 1.2,
  "letter_spacing": 0,
  "animation": {
    "type": "fade_in",
    "duration": 1.0
  }
}
```

---

> **文档版本**：v1.0  
> **最后更新**：2026-05-14  
> **适用项目**：CapCutAPI-Complete