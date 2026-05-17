# pyJianYingDraft 项目开发说明文档

> pyJianYingDraft_development_guide.md

> 轻量、灵活、易上手的 Python 剪映草稿生成及导出工具，构建全自动视频剪辑/混剪流水线

  

---

## 目录


1. [剪映草稿核心概念](#1-剪映草稿核心概念)
2. [项目架构总览](#2-项目架构总览)
3. [模块关系与编码逻辑](#3-模块关系与编码逻辑)
4. [开发周期一：基础框架搭建](#4-开发周期一基础框架搭建)
5. [开发周期二：音视频片段系统](#5-开发周期二音视频片段系统)
6. [开发周期三：特效、滤镜与转场](#6-开发周期三特效滤镜与转场)
7. [开发周期四：模板模式与自动化导出](#7-开发周期四模板模式与自动化导出)
8. [开发周期五：高级特性与工程完善](#8-开发周期五高级特性与工程完善)
9. [操作方法与注意事项](#9-操作方法与注意事项)

  

---


## 1. 剪映草稿核心概念

### 1.1 什么是剪映草稿？

剪映（JianYing Pro）是一款视频编辑软件。用户在剪映中编辑视频时，所有编辑操作都会被保存为一个**草稿（Draft）**。每个草稿在磁盘上对应一个文件夹，其中包含两个核心文件：

| 文件                     | 作用                               |
| ---------------------- | -------------------------------- |
| `draft_content.json`   | 草稿的**核心数据文件**，包含所有轨道、片段、素材、特效等信息 |
| `draft_meta_info.json` | 草稿的**元信息文件**，包含草稿名称、创建时间、封面等     |

**pyJianYingDraft 的核心原理**：通过程序生成符合剪映规范的 `draft_content.json` 文件，从而让剪映能够识别并打开程序生成的草稿。

### 1.2 草稿内部的核心概念

理解以下概念是理解整个项目的关键：
#### 1.2.1 轨道（Track）

轨道是时间轴上的"层"，不同类型的媒体内容放在不同类型的轨道上：

| 轨道类型      | 说明   | 可放置的片段                |
| --------- | ---- | --------------------- |
| `video`   | 视频轨道 | VideoSegment（视频/图片片段） |
| `audio`   | 音频轨道 | AudioSegment（音频片段）    |
| `text`    | 文本轨道 | TextSegment（文本/字幕片段）  |
| `sticker` | 贴纸轨道 | StickerSegment（贴纸片段）  |
| `effect`  | 特效轨道 | EffectSegment（独立特效片段） |
| `filter`  | 滤镜轨道 | FilterSegment（独立滤镜片段） |

- 同一类型的轨道可以有**多条**（如多条视频轨道实现画中画效果）
- 每条轨道有一个 `render_index`（渲染顺序），值越大越接近前景
- 主视频轨道（最底层的视频轨道）上的片段必须从 0s 开始
#### 1.2.2 片段（Segment）

片段是时间轴上的一个"块"，代表一段具体的媒体内容。每个片段包含：

- **`target_timerange`**：片段在轨道上的时间范围（起始时间 + 持续时长）
- **`source_timerange`**：从素材中截取的时间范围（用于裁剪素材）
- **`material_id`**：引用的素材 ID
- **`speed`**：播放速度
- **`volume`**：音量
- **`clip_settings`**：图像调节设置（位置、缩放、旋转、透明度等）

#### 1.2.3 素材（Material）

素材是媒体文件的抽象表示。一份素材可以被多个片段引用：

- **`VideoMaterial`**：视频或图片素材，包含路径、时长、尺寸等信息
- **`AudioMaterial`**：音频素材，包含路径、时长等信息
- 贴纸、文本等也有对应的素材表示
#### 1.2.4 时间系统

整个项目使用**微秒（μs）**作为时间单位：

```
1 秒 = 1,000,000 微秒
```

项目提供了便捷的时间工具：

- `tim("1s")` → 将字符串转为微秒数（`1000000`）
- `trange("0s", "5s")` → 创建时间范围（从 0s 开始，持续 5s）
- `Timerange(start, duration)` → 时间范围对象

#### 1.2.5 关键帧（Keyframe）

关键帧用于在时间轴上动态改变属性值（如位置、缩放、透明度等）。每个关键帧包含：
- `time_offset`：相对于片段起始点的时间偏移
- `values`：该时间点的属性值
- 关键帧之间使用**线性插值**
#### 1.2.6 动画（Animation）

动画是预设的视觉效果，分为：
- **入场动画（Intro）**：片段开始时的动画
- **出场动画（Outro）**：片段结束时的动画
- **组合动画（Group）**：贯穿整个片段的动画（仅视频）
- **循环动画（Loop）**：持续循环的动画（仅文本）
#### 1.2.7 特效与滤镜

- **特效（Effect）**：作用于片段的视觉效果（如"模糊"、"马赛克"等）
- **滤镜（Filter）**：色彩调整效果（如"复古"、"冷白"等）
- **转场（Transition）**：两个片段之间的过渡效果
- **蒙版（Mask）**：限制片段可见区域的形状

---
## 2. 项目架构总览
### 2.1 整体架构图

```

┌─────────────────────────────────────────────────────────────┐
│                      用户代码层                              │
│  demo.py / 用户自己的脚本                                    │
│  使用 DraftFolder 创建/加载草稿，添加轨道和片段，保存草稿      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    对外接口层 (__init__.py)                   │
│  统一导出所有公共类、枚举、函数                                │
│  提供向后兼容的旧命名别名                                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    核心业务层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ DraftFolder  │  │  ScriptFile  │  │JianyingCtrl  │       │
│  │ 草稿文件夹管理│  │  草稿文件核心 │  │ 剪映自动化   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                  │               │
│  ┌──────▼─────────────────▼──────────────────▼───────┐       │
│  │                  Track (轨道)                      │       │
│  │  管理同类型片段，控制渲染层级                        │       │
│  └──────────────────────┬───────────────────────────┘       │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────┐       │
│  │               Segment (片段)                       │       │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │       │
│  │  │  Video   │ │  Audio   │ │   Text   │  ...     │       │
│  │  │ Segment  │ │ Segment  │ │ Segment  │          │       │
│  │  └──────────┘ └──────────┘ └──────────┘          │       │
│  └──────────────────────────────────────────────────┘       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    素材与元数据层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │VideoMaterial │  │AudioMaterial │  │  metadata/   │       │
│  │  视频素材    │  │  音频素材    │  │  特效元数据   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    基础设施层                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │time_util │ │ keyframe │ │animation │ │  util    │       │
│  │ 时间工具 │ │ 关键帧   │ │  动画    │ │ 辅助函数 │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐                                 │
│  │ assets/  │ │exceptions│                                 │
│  │ 模板资源 │ │ 异常定义 │                                 │
│  └──────────┘ └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘

```

### 2.2 文件结构说明

```

pyJianYingDraft/
├── __init__.py              # 包入口，统一导出所有公共接口
├── draft_folder.py          # 草稿文件夹管理器
├── script_file.py           # 草稿文件核心（最核心的类）
├── track.py                 # 轨道类及轨道类型枚举
├── segment.py               # 片段基类及通用属性类
├── video_segment.py         # 视频/贴纸片段及相关类
├── audio_segment.py         # 音频片段及相关类
├── text_segment.py          # 文本片段及相关类
├── effect_segment.py        # 特效/滤镜片段类
├── local_materials.py       # 本地素材类（视频/音频）
├── keyframe.py              # 关键帧系统
├── animation.py             # 动画系统
├── time_util.py             # 时间工具（Timerange, tim, trange）
├── template_mode.py         # 模板模式相关类
├── jianying_controller.py   # 剪映自动化控制（仅Windows）
├── util.py                  # 辅助函数
├── exceptions.py            # 自定义异常类
├── assets/                  # 资源文件
│   ├── __init__.py          # 资源管理模块
│   ├── draft_content_template.json  # 草稿JSON模板
│   └── draft_meta_info.json # 草稿元信息模板
└── metadata/                # 元数据定义
    ├── __init__.py          # 元数据包入口
    ├── effect_meta.py       # 元数据基类定义
    ├── filter_meta.py       # 滤镜元数据
    ├── transition_meta.py   # 转场元数据
    ├── font_meta.py         # 字体元数据
    ├── mask_meta.py         # 蒙版元数据
    ├── mix_mode_meta.py     # 混合模式元数据
    ├── video_scene_effect.py # 视频场景特效
    ├── video_character_effect.py # 视频人物特效
    ├── audio_scene_effect.py # 音频场景音效
    ├── tone_effect.py       # 音色效果
    ├── speech_to_song.py    # 声音成曲效果
    ├── video_intro.py       # 视频入场动画
    ├── video_outro.py       # 视频出场动画
    ├── video_group_animation.py # 视频组合动画
    ├── text_intro.py        # 文本入场动画
    ├── text_outro.py        # 文本出场动画
    └── text_loop.py         # 文本循环动画

```

### 2.3 类继承关系

```

BaseSegment (片段基类)
├── MediaSegment (媒体片段基类)
│   ├── VisualSegment (视觉片段基类)
│   │   ├── VideoSegment (视频/图片片段)
│   │   ├── StickerSegment (贴纸片段)
│   │   └── TextSegment (文本片段)
│   └── AudioSegment (音频片段)
├── EffectSegment (独立特效片段)
└── FilterSegment (独立滤镜片段) 

BaseTrack (轨道基类)
├── Track (普通轨道)
└── ImportedTrack (导入轨道)
    └── EditableTrack (可编辑导入轨道)
        ├── ImportedMediaTrack (导入的音视频轨道)
        └── ImportedTextTrack (导入的文本轨道)

```

  

---

## 3. 模块关系与编码逻辑
### 3.1 核心数据流

```

用户代码

  │
  ├─→ DraftFolder.create_draft()  →  创建 ScriptFile
  │     ├─ 创建草稿文件夹
  │     ├─ 复制 draft_meta_info.json 模板
  │     └─ 初始化 ScriptFile（加载 draft_content_template.json）
  │
  ├─→ ScriptFile.add_track()  →  创建 Track
  │     └─ 指定轨道类型、名称、渲染层级
  │
  ├─→ 创建 Segment（VideoSegment/AudioSegment/TextSegment）
  │     ├─ 自动创建 Material（VideoMaterial/AudioMaterial）
  │     ├─ 可选添加动画、特效、滤镜、转场等
  │     └─ 可选添加关键帧
  │
  ├─→ ScriptFile.add_segment()  →  将片段加入轨道
  │     ├─ 检查片段类型与轨道类型匹配
  │     ├─ 检查片段不与已有片段重叠
  │     ├─ 自动将相关素材加入 ScriptMaterial
  │     └─ 更新草稿总时长
  │
  └─→ ScriptFile.save()  →  导出 draft_content.json
        ├─ 合并所有素材信息
        ├─ 合并导入的素材（模板模式）
        ├─ 按 render_index 排序所有轨道
        └─ 写入 JSON 文件

```

### 3.2 JSON 导出机制

每个需要导出到 JSON 的类都实现了 `export_json()` 方法，返回一个字典。最终由 `ScriptFile.dumps()` 方法递归组装成完整的 JSON 结构：

```python

# 导出层次结构
ScriptFile.dumps()
  ├─ materials.export_json()     # 素材信息
  │   ├─ audios: [AudioMaterial.export_json()]
  │   ├─ videos: [VideoMaterial.export_json()]
  │   ├─ effects: [Filter.export_json(), MixMode.export_json()]
  │   ├─ video_effects: [VideoEffect.export_json()]
  │   ├─ audio_effects: [AudioEffect.export_json()]
  │   ├─ audio_fades: [AudioFade.export_json()]
  │   ├─ animations: [SegmentAnimations.export_json()]
  │   ├─ transitions: [Transition.export_json()]
  │   ├─ speeds: [Speed.export_json()]
  │   ├─ masks: [Mask.export_json()]
  │   ├─ canvases: [BackgroundFilling.export_json()]
  │   ├─ texts: [TextSegment.export_material()]
  │   └─ stickers: [StickerSegment.export_material()]
  │
  └─ tracks: [Track.export_json()]
      └─ segments: [Segment.export_json()]
          ├─ 基础属性 (id, material_id, target_timerange)
          ├─ common_keyframes: [KeyframeList.export_json()]
          ├─ clip: ClipSettings.export_json()
          ├─ source_timerange, speed, volume
          └─ extra_material_refs (关联的动画/特效/滤镜ID)
```

### 3.3 元数据系统设计

元数据系统使用 Python 枚举（Enum）来组织大量的特效、滤镜、转场等数据：

```python

# 元数据基类

class EffectMeta:
    name: str          # 效果名称
    resource_id: str   # 资源ID
    effect_id: str     # 效果ID
    md5: str           # MD5校验
    params: List[EffectParam]  # 可调参数列表 

# 枚举类（以转场为例）

class TransitionType(EffectEnum):
    叠化 = TransitionMeta("叠化", False, "6724845717472416269",
                         "322577", "2d641adc...", 0.500, True)

    模糊 = TransitionMeta("模糊", False, "6911569618171597320",
                         "4212596", "fc135243...", 0.500, True)
    # ... 更多转场

```

这种设计的好处：
- 枚举成员名即为中文名称，直观易用
- 每个枚举成员携带完整的元数据
- 通过 `EffectEnum.from_name()` 可以根据名称查找特效
### 3.4 模板模式设计

模板模式允许加载已有的剪映草稿作为模板，然后进行修改：

```

ScriptFile.load_template(json_path)
  ├─ 读取 draft_content.json
  ├─ 解析基础属性 (fps, duration, width, height)
  ├─ 导入素材 → imported_materials
  └─ 导入轨道 → imported_tracks
      └─ import_track() 根据轨道类型创建不同的 ImportedTrack 子类

模板模式下的操作：

  ├─ replace_material_by_name()  →  替换素材本身
  ├─ replace_material_by_seg()   →  替换特定片段的素材
  ├─ replace_text()              →  替换文本内容
  ├─ import_track()              →  从模板导入轨道到新草稿
  └─ inspect_material()          →  提取贴纸/气泡/花字元数据

```

### 3.5 关键设计决策 

1. **微秒作为时间单位**：与剪映内部格式保持一致，避免浮点精度问题
2. **UUID 作为 ID**：所有素材、片段、特效等都使用 `uuid.uuid4().hex` 生成唯一 ID
3. **链式调用**：大部分方法返回 `self`，支持链式调用（如 `script.add_track().add_track()`）
4. **自动素材管理**：添加片段时自动将相关素材注册到 `ScriptMaterial` 中
5. **deepcopy 素材实例**：片段持有素材的深拷贝，避免多个片段共享同一素材实例导致的问题

---
## 4. 开发周期一：基础框架搭建

> **难度**：★☆☆☆☆ | **目标**：搭建项目骨架，实现最基础的草稿创建和保存功能

### 4.1 任务清单

| 序号   | 任务                             | 涉及文件                           |
| ---- | ------------------------------ | ------------------------------ |
| 1.1  | 创建项目目录结构                       | 全部                             |
| 1.2  | 实现时间工具模块                       | `time_util.py`                 |
| 1.3  | 实现自定义异常类                       | `exceptions.py`                |
| 1.4  | 准备 JSON 模板资源                   | `assets/`                      |
| 1.5  | 实现资源管理模块                       | `assets/__init__.py`           |
| 1.6  | 实现片段基类                         | `segment.py`                   |
| 1.7  | 实现轨道类                          | `track.py`                     |
| 1.8  | 实现草稿文件核心类                      | `script_file.py`               |
| 1.9  | 实现草稿文件夹管理器                     | `draft_folder.py`              |
| 1.10 | 实现包入口                          | `__init__.py`                  |
| 1.11 | 编写 setup.py 和 requirements.txt | `setup.py`, `requirements.txt` |
| 1.12 | 编写 demo.py 验证基础功能              | `demo.py`                      |
|      |                                |                                |

### 4.2 详细步骤

#### 步骤 1.1：创建项目目录结构

```

pyJianYingDraft/
├── pyJianYingDraft/       # 主包目录
│   ├── __init__.py
│   ├── assets/            # 资源目录
│   │   └── __init__.py
│   └── metadata/          # 元数据目录（本周期暂不填充）
│       └── __init__.py
├── demo.py                # 示例脚本
├── setup.py               # 安装配置
└── requirements.txt       # 依赖声明

```

#### 步骤 1.2：实现时间工具模块 (`time_util.py`)

这是整个项目最基础的模块，所有时间计算都依赖它。

**核心内容**：

- `SEC = 1000000`：定义 1 秒 = 1,000,000 微秒
- `tim(inp)`：将字符串（如 `"1h52m3s"`、`"0.15s"`）或数值转换为微秒数
- `Timerange` 类：记录起始时间和持续时长，提供 `start`、`duration`、`end` 属性，支持重叠判断
- `trange(start, duration)`：`Timerange` 的便捷构造函数
- `srt_tstamp(tstamp)`：解析 SRT 字幕时间戳

**关键实现细节**：

```python

class Timerange:
    def __init__(self, start: int, duration: int):
        self.start = start      # 起始时间（微秒）
        self.duration = duration # 持续时长（微秒）

    @property
    def end(self) -> int:
        return self.start + self.duration 

    def overlaps(self, other: "Timerange") -> bool:
        return not (self.end <= other.start or other.end <= self.start)

```

#### 步骤 1.3：实现自定义异常类 (`exceptions.py`)

定义项目中会用到的所有异常类型：

```python

class TrackNotFound(NameError): ...     # 未找到轨道
class AmbiguousTrack(ValueError): ...   # 找到多个轨道
class SegmentOverlap(ValueError): ...   # 片段重叠
class MaterialNotFound(NameError): ...  # 未找到素材
class AmbiguousMaterial(ValueError): ...# 找到多个素材
class ExtensionFailed(ValueError): ...  # 延伸失败
class DraftNotFound(NameError): ...     # 未找到草稿
class AutomationError(Exception): ...   # 自动化操作失败
class ExportTimeout(Exception): ...     # 导出超时

```

#### 步骤 1.4：准备 JSON 模板资源

从剪映导出一个空的草稿，提取其 `draft_content.json` 作为模板。模板中需要包含剪映期望的所有顶层字段（如 `fps`、`duration`、`canvas_config`、`config`、`materials`、`tracks` 等），但内容为空或默认值。

同时准备 `draft_meta_info.json` 模板。
#### 步骤 1.5：实现资源管理模块 (`assets/__init__.py`)

提供 `get_asset_path(asset_name)` 函数，根据资源名称返回模板文件的完整路径。使用 `Path(__file__).parent` 定位资源目录，避免硬编码路径。
#### 步骤 1.6：实现片段基类 (`segment.py`)

**核心类**：

1. **`BaseSegment`**：所有片段的基类
   - `segment_id`：UUID 生成的唯一 ID
   - `material_id`：引用的素材 ID
   - `target_timerange`：在轨道上的时间范围
   - `common_keyframes`：关键帧列表
   - `export_json()`：导出基础 JSON 属性

2. **`Speed`**：播放速度对象
   - `speed`：速度值
   - `export_json()`：导出 JSON

3. **`AudioFade`**：音频淡入淡出效果
   - `in_duration`、`out_duration`：淡入/淡出时长

4. **`ClipSettings`**：图像调节设置
   - `alpha`：不透明度
   - `flip_horizontal`、`flip_vertical`：翻转
   - `rotation`：旋转角度
   - `scale_x`、`scale_y`：缩放
   - `transform_x`、`transform_y`：位移

5. **`MediaSegment`**：媒体片段基类（继承 `BaseSegment`）
   - `source_timerange`：素材截取范围
   - `speed`：播放速度
   - `volume`：音量
   - `change_pitch`：变速是否变调
   - `extra_material_refs`：关联的附加素材 ID

6. **`VisualSegment`**：视觉片段基类（继承 `MediaSegment`）
   - `clip_settings`：图像调节
   - `uniform_scale`：是否锁定缩放比例
   - `animations_instance`：动画实例
   - `add_keyframe()`：添加关键帧

#### 步骤 1.7：实现轨道类 (`track.py`)

**核心内容**：

1. **`Track_meta`**：轨道元数据 dataclass

   - `segment_type`：允许的片段类型
   - `render_index`：默认渲染顺序
   - `allow_modify`：导入时是否允许修改

  
2. **`TrackType`**：轨道类型枚举

   - `video`、`audio`、`text`、`sticker`、`effect`、`filter`、`adjust`
   - 每个成员关联一个 `Track_meta` 实例


3. **`BaseTrack`**：轨道抽象基类

   - `track_type`、`name`、`track_id`、`render_index`

  
4. **`Track`**：普通轨道类（泛型类）

   - `segments`：片段列表
   - `add_segment()`：添加片段（检查类型匹配和重叠）
   - `export_json()`：导出轨道 JSON

#### 步骤 1.8：实现草稿文件核心类 (`script_file.py`)

这是整个项目**最核心**的类，需要在本周期实现以下功能：

1. **`ScriptMaterial`**：素材管理器

   - 管理所有类型的素材列表（音频、视频、特效、动画等）
   - `export_json()`：将所有素材导出为 JSON


2. **`ScriptFile`**：草稿文件类

   - `__init__()`：初始化草稿（加载模板 JSON）
   - `add_track()`：添加轨道
   - `add_segment()`：添加片段到轨道（自动注册素材）
   - `dumps()`：导出完整 JSON 字符串
   - `dump()`：写入 JSON 文件
   - `save()`：保存到打开时的路径
 

**关键逻辑**：`add_segment()` 方法需要：

1. 根据片段类型找到对应轨道
2. 检查片段不重叠
3. 将片段加入轨道
4. 自动将相关素材（动画、特效、滤镜等）注册到 `ScriptMaterial`
5. 更新草稿总时长
#### 步骤 1.9：实现草稿文件夹管理器 (`draft_folder.py`)

```python

class DraftFolder:
    def __init__(self, folder_path: str): ...
    def list_drafts(self) -> List[str]: ...     # 列出所有草稿
    def has_draft(self, draft_name: str): ...   # 检查草稿是否存在
    def remove(self, draft_name: str): ...      # 删除草稿
    def create_draft(self, draft_name, width, height, fps=30, *,
                     allow_replace=False) -> ScriptFile: ...
        # 1. 创建草稿文件夹

        # 2. 复制 draft_meta_info.json

        # 3. 创建 ScriptFile 实例

        # 4. 设置保存路径

```

#### 步骤 1.10：实现包入口 (`__init__.py`)

统一导出所有公共类、枚举和函数，方便用户使用：

```python

from .draft_folder import DraftFolder
from .script_file import ScriptFile
from .track import TrackType
from .time_util import Timerange, tim, trange, SEC
# ... 更多导出

```

#### 步骤 1.11：编写 setup.py 和 requirements.txt

```python

# setup.py
setup(
    name="pyjianyingdraft",
    version="0.1.0",
    packages=find_packages(),
    package_data={'pyJianYingDraft': ['assets/*.json']},
    install_requires=["pymediainfo", "imageio"],
)

```

#### 步骤 1.12：编写 demo.py 验证

创建一个最简单的 demo：创建草稿、添加轨道、保存，然后在剪映中打开验证。
### 4.3 周期一验收标准

- [ ] 能够通过 `DraftFolder.create_draft()` 创建一个空草稿
- [ ] 能够添加不同类型的轨道
- [ ] 能够调用 `save()` 保存草稿
- [ ] 剪映能够识别并打开生成的草稿
- [ ] 时间工具函数正确工作
- [ ] 异常处理机制正常工作

---

## 5. 开发周期二：音视频片段系统
 

> **难度**：★★★☆☆ | **目标**：实现完整的音视频片段功能，包括素材加载、片段创建、关键帧和动画

### 5.1 任务清单

| 序号   | 任务                    | 涉及文件                        |
| ---- | --------------------- | --------------------------- |
| 2.1  | 实现本地素材类               | `local_materials.py`        |
| 2.2  | 实现音频片段类               | `audio_segment.py`          |
| 2.3  | 实现视频片段类               | `video_segment.py`          |
| 2.4  | 实现关键帧系统               | `keyframe.py`               |
| 2.5  | 实现动画系统                | `animation.py`              |
| 2.6  | 实现元数据基类               | `metadata/effect_meta.py`   |
| 2.7  | 实现视频动画元数据             | `metadata/video_intro.py` 等 |
| 2.8  | 实现文本动画元数据             | `metadata/text_intro.py` 等  |
| 2.9  | 实现蒙版元数据               | `metadata/mask_meta.py`     |
| 2.10 | 更新 ScriptFile 支持新片段类型 | `script_file.py`            |
| 2.11 | 更新 demo.py 验证完整功能     | `demo.py`                   |

### 5.2 详细步骤

#### 步骤 2.1：实现本地素材类 (`local_materials.py`)

**`VideoMaterial`**：

- 使用 `pymediainfo` 库解析视频/图片文件的元信息（时长、尺寸等）
- 支持 mp4、mov、avi 等视频格式和 jpg、png 等图片格式
- GIF 文件使用 `imageio` 库获取时长
- 图片素材的 `duration` 设为 3 小时（10800000000 微秒）
- 提供 `export_json()` 方法导出素材 JSON

**`AudioMaterial`**：

- 使用 `pymediainfo` 解析音频文件
- 检查不包含视频轨道
- 提供 `export_json()` 方法

**`CropSettings`**：

- 素材裁剪设置，四个角的坐标（0-1 范围）

  

#### 步骤 2.2：实现音频片段类 (`audio_segment.py`)

**`AudioEffect`**：音频特效对象

- 支持场景音（`AudioSceneEffectType`）、音色（`ToneEffectType`）、声音成曲（`SpeechToSongType`）
- 参数解析和导出
  

**`AudioSegment`**（继承 `MediaSegment`）：

- 构造函数支持传入素材路径或 `AudioMaterial` 实例
- 自动计算 `source_timerange` 和 `speed`
- `add_fade(in_duration, out_duration)`：添加淡入淡出
- `add_effect(effect_type, params)`：添加音频特效
- `add_keyframe(time_offset, volume)`：添加音量关键帧

  

#### 步骤 2.3：实现视频片段类 (`video_segment.py`)

本模块包含大量类，是项目中最复杂的模块之一：

1. **`Mask`**：蒙版对象
2. **`VideoEffect`**：视频特效素材
3. **`Filter`**：滤镜素材
4. **`Transition`**：转场对象
5. **`BackgroundFilling`**：背景填充对象
6. **`MixMode`**：混合模式对象
7. **`VideoSegment`**（继承 `VisualSegment`）：

   - `add_animation(type, duration)`：添加入场/出场/组合动画
   - `add_effect(type, params)`：添加视频特效
   - `add_fade(in, out)`：添加音频淡入淡出
   - `add_filter(type, intensity)`：添加滤镜
   - `set_mix_mode(mode)`：设置混合模式
   - `add_mask(type, ...)`：添加蒙版
   - `add_transition(type, duration)`：添加转场
   - `add_background_filling(type, ...)`：添加背景填充

  
8. **`StickerSegment`**（继承 `VisualSegment`）：

   - 通过 `resource_id` 引用贴纸资源

#### 步骤 2.4：实现关键帧系统 (`keyframe.py`)

  

1. **`Keyframe`**：单个关键帧

   - `time_offset`：时间偏移
   - `values`：值列表
   - 支持线性插值（`curveType: "Line"`）


2. **`KeyframeProperty`**：关键帧属性枚举

   - `position_x`、`position_y`：位置
   - `rotation`：旋转
   - `scale_x`、`scale_y`、`uniform_scale`：缩放
   - `alpha`：不透明度
   - `saturation`、`contrast`、`brightness`：色彩调整
   - `volume`：音量

  

3. **`KeyframeList`**：关键帧列表

   - 管理同一属性的多个关键帧
   - `add_keyframe(time_offset, value)`：添加并自动排序

#### 步骤 2.5：实现动画系统 (`animation.py`)


1. **`Animation`**：动画基类

   - `name`、`effect_id`、`resource_id`
   - `start`、`duration`：动画时间范围

  

2. **`VideoAnimation`**：视频动画（入场/出场/组合）

  
3. **`Text_animation`**：文本动画（入场/出场/循环）


4. **`SegmentAnimations`**：片段动画集合

   - 管理一个片段上的所有动画
   - 限制：不能同时有组合动画和出入场动画
   - 限制：文本循环动画需在出入场动画之后添加

#### 步骤 2.6：实现元数据基类 (`metadata/effect_meta.py`) 

1. **`EffectParam`**：特效参数定义（名称、默认值、范围）
2. **`EffectParamInstance`**：特效参数实例（继承 `EffectParam`，增加当前值）
3. **`EffectMeta`**：特效元数据（名称、VIP状态、resource_id、effect_id、参数列表）
4. **`EffectEnum`**：特效枚举基类，提供 `from_name()` 方法
5. **`AnimationMeta`**：动画元数据
6. **`MaskMeta`**：蒙版元数据
7. **`TransitionMeta`**：转场元数据

#### 步骤 2.7-2.9：实现各类元数据枚举

按照从剪映中提取的数据，创建以下枚举类：

- `IntroType`、`OutroType`、`GroupAnimationType`（视频动画）
- `TextIntro`、`TextOutro`、`TextLoopAnim`（文本动画）
- `MaskType`（蒙版类型）
- `FontType`（字体类型）

#### 步骤 2.10：更新 ScriptFile

在 `add_segment()` 方法中增加对新片段类型的支持：

- `VideoSegment`：自动注册动画、淡入淡出、特效、滤镜、蒙版、转场、背景填充、变速
- `AudioSegment`：自动注册淡入淡出、特效、变速
- `StickerSegment`：自动注册贴纸素材

#### 步骤 2.11：更新 demo.py

创建一个完整的 demo：

1. 添加音频片段（带淡入效果和音量调节）
2. 添加视频片段（带入场动画）
3. 添加贴纸片段（带背景填充）
4. 添加转场效果
5. 保存并在剪映中验证
### 5.3 周期二验收标准

- [ ] 能够加载本地音视频文件作为素材
- [ ] 能够创建音视频片段并指定时间范围
- [ ] 能够添加关键帧控制位置、缩放、透明度等
- [ ] 能够添加入场/出场动画
- [ ] 能够添加蒙版效果
- [ ] 能够添加音频淡入淡出
- [ ] 剪映中打开草稿后所有效果正确显示

---

## 6. 开发周期三：特效、滤镜与转场

> **难度**：★★★☆☆ | **目标**：实现完整的特效、滤镜、转场系统，以及文本片段功能
### 6.1 任务清单

| 序号   | 任务                      | 涉及文件                               |
| ---- | ----------------------- | ---------------------------------- |
| 3.1  | 实现特效/滤镜片段类              | `effect_segment.py`                |
| 3.2  | 实现文本片段类                 | `text_segment.py`                  |
| 3.3  | 实现滤镜元数据                 | `metadata/filter_meta.py`          |
| 3.4  | 实现转场元数据                 | `metadata/transition_meta.py`      |
| 3.5  | 实现视频特效元数据               | `metadata/video_scene_effect.py` 等 |
| 3.6  | 实现音频特效元数据               | `metadata/audio_scene_effect.py` 等 |
| 3.7  | 实现混合模式元数据               | `metadata/mix_mode_meta.py`        |
| 3.8  | 实现字体元数据                 | `metadata/font_meta.py`            |
| 3.9  | 更新 ScriptFile 支持特效/滤镜轨道 | `script_file.py`                   |
| 3.10 | 实现 SRT 字幕导入功能           | `script_file.py`                   |
| 3.11 | 更新 demo.py 验证完整功能       | `demo.py`                          |

### 6.2 详细步骤

#### 步骤 3.1：实现特效/滤镜片段类 (`effect_segment.py`)

1. **`EffectSegment`**：独立特效轨道上的特效片段

   - 特效作用域为全局（`apply_target_type=2`）
   - 支持视频场景特效和人物特效


2. **`FilterSegment`**：独立滤镜轨道上的滤镜片段

   - 支持调节强度的滤镜

#### 步骤 3.2：实现文本片段类 (`text_segment.py`)

这是功能最丰富的片段类型之一：


1. **`TextStyle`**：字体样式

   - `size`、`bold`、`italic`、`underline`
   - `color`（RGB 三元组，0-1 范围）、`alpha`
   - `align`（左/中/右对齐）、`vertical`（竖排）
   - `letter_spacing`、`line_spacing`
   - `auto_wrapping`、`max_line_width`（自动换行）

  
2. **`TextBorder`**：文本描边

   - `alpha`、`color`、`width`

3. **`TextBackground`**：文本背景

   - `style`、`color`、`alpha`、`round_radius` 等


4. **`TextShadow`**：文本阴影

   - `alpha`、`color`、`diffuse`、`distance`、`angle`

  
5. **`TextBubble`**：文本气泡效果

  
6. **`TextEffect`**：文本花字效果

  
7. **`TextSegment`**（继承 `VisualSegment`）：

   - `add_animation(type, duration)`：添加文本动画
   - `add_bubble(effect_id, resource_id)`：添加气泡效果
   - `add_effect(effect_id)`：添加花字效果
   - `create_from_template(text, timerange, template)`：从模板创
   - `export_material()`：导出文本素材 JSON

#### 步骤 3.3-3.8：实现各类元数据

从剪映中提取并整理以下元数据：

- **滤镜**：数百种滤镜效果，部分支持强度调节
- **转场**：上百种转场效果，各有默认时长
- **视频特效**：场景特效和人物特效，各有参数
- **音频特效**：场景音、音色、声音成曲
- **混合模式**：正片叠底、滤色、叠加等
- **字体**：数百种字体资源

每种元数据都定义为枚举类，继承 `EffectEnum`。

#### 步骤 3.9：更新 ScriptFile

增加以下方法：

- `add_effect(effect_type, t_range, track_name, params)`：向特效轨道添加特效片段
- `add_filter(filter_meta, t_range, track_name, intensity)`：向滤镜轨道添加滤镜片段
#### 步骤 3.10：实现 SRT 字幕导入 

`ScriptFile.import_srt(srt_path, track_name, ...)`：

1. 解析 SRT 文件格式（序号 → 时间戳 → 内容）
2. 为每条字幕创建 `TextSegment`
3. 支持时间偏移、样式参考、自定义样式
#### 步骤 3.11：更新 demo.py

扩展 demo 以展示：
1. 文本片段（带字体、颜色、气泡、花字效果）
2. 独立特效轨道上的特效
3. 独立滤镜轨道上的滤镜
4. SRT 字幕导入
### 6.3 周期三验收标准

- [ ] 能够创建文本片段并设置字体、样式、描边、阴影
- [ ] 能够添加文本气泡和花字效果
- [ ] 能够添加独立特效和滤镜轨道
- [ ] 能够导入 SRT 字幕文件
- [ ] 所有元数据枚举正确可用
- [ ] 剪映中打开草稿后文本和特效正确显示

---

## 7. 开发周期四：模板模式与自动化导出

> **难度**：★★★★☆ | **目标**：实现模板模式（加载已有草稿进行修改）和 Windows 下的自动化导出
### 7.1 任务清单

| 序号   | 任务                    | 涉及文件                     |
| ---- | --------------------- | ------------------------ |
| 4.1  | 实现模板模式核心类             | `template_mode.py`       |
| 4.2  | 实现辅助函数                | `util.py`                |
| 4.3  | 更新 ScriptFile 支持模板模式  | `script_file.py`         |
| 4.4  | 更新 DraftFolder 支持模板操作 | `draft_folder.py`        |
| 4.5  | 实现剪映自动化控制器            | `jianying_controller.py` |
| 4.6  | 实现素材替换功能              | `script_file.py`         |
| 4.7  | 实现文本替换功能              | `script_file.py`         |
| 4.8  | 实现轨道导入功能              | `script_file.py`         |
| 4.9  | 实现素材元数据提取             | `script_file.py`         |
| 4.10 | 更新包入口和平台兼容            | `__init__.py`            |

### 7.2 详细步骤

#### 步骤 4.1：实现模板模式核心类 (`template_mode.py`)

1. **`ShrinkMode`**：素材变短时的处理方式

   - `cut_head`：裁剪头部
   - `cut_tail`：裁剪尾部
   - `cut_tail_align`：裁剪尾部并消除间隙
   - `shrink`：两端向中间靠拢


2. **`ExtendMode`**：素材变长时的处理方式

   - `cut_material_tail`：裁剪素材尾部（维持原长）
   - `extend_head`：延伸头部
   - `extend_tail`：延伸尾部
   - `push_tail`：延伸尾部并后移后续片段


3. **`ImportedSegment`**：导入的片段（保留原始 JSON）

4. **`ImportedMediaSegment`**：导入的音视频片段

5. **`ImportedTrack`**：导入的轨道基类

6. **`EditableTrack`**：可编辑的导入轨道

7. **`ImportedMediaTrack`**：导入的音视频轨道（支持素材替换）

8. **`ImportedTextTrack`**：导入的文本轨道（支持文本替换）

9. **`import_track(track_data)`**：工厂函数，根据轨道类型创建对应的导入轨道

  

#### 步骤 4.2：实现辅助函数 (`util.py`)

- `provide_ctor_defaults(cls)`：为构造函数提供默认值（用于绕过参数限制加载模板）
- `assign_attr_with_json(obj, attrs, json_data)`：从 JSON 数据赋值对象属性
- `export_attr_to_json(obj, attrs)`：将对象属性导出为 JSON

#### 步骤 4.3：更新 ScriptFile 支持模板模式

增加以下功能：

- `load_template(json_path)`：静态方法，从 JSON 文件加载模板
- `imported_materials`：导入的素材字典
- `imported_tracks`：导入的轨道列表
- `dumps()` 方法合并导入的素材和轨道

#### 步骤 4.4：更新 DraftFolder 支持模板操作

增加以下方法：

- `load_template(draft_name)`：加载草稿作为模板
- `duplicate_as_template(template_name, new_draft_name)`：复制草稿并作为模板打开
- `inspect_material(draft_name)`：提取草稿中的素材元数据

#### 步骤 4.5：实现剪映自动化控制器 (`jianying_controller.py`)

> ⚠️ 此功能仅支持 Windows 系统

使用 `uiautomation` 库控制剪映 GUI：

1. **`ControlFinder`**：控件查找器

   - `desc_matcher()`：根据 `full_description` 查找控件
   - `class_name_matcher()`：根据 `ClassName` 查找控件

  
2. **`JianyingController`**：剪映控制器

   - `get_window()`：获取剪映窗口
   - `switch_to_home()`：切换到主页
   - `export_draft(draft_name, output_path, resolution, framerate, timeout)`：

     2. 在主页找到对应草稿并点击
     3. 等待进入编辑模式
     4. 点击导出按钮
     5. 设置分辨率和帧率（可选）
     6. 点击确认导出
     7. 等待导出完成
     8. 复制导出文件到指定路径

3.**`ExportResolution`**、**`ExportFramerate`**：导出参数枚举

  

#### 步骤 4.6-4.9：实现模板编辑功能

  
1. **`replace_material_by_name(material_name, material)`**：

   - 根据素材名称查找并替换素材
   - 更新路径、时长、尺寸等信息
   - 适合图片素材替换

  

2. **`replace_material_by_seg(track, segment_index, material, ...)`**：

   - 替换特定片段的素材
   - 支持重新指定截取范围
   - 支持处理时长变化（`ShrinkMode`/`ExtendMode`）

3. **`replace_text(track, segment_index, text)`**：

   - 替换文本片段内容
   - 支持普通文本和文本模板
   - 自动重新计算样式分布

4. **`import_track(source_file, track, offset, new_name)`**：

   - 从模板草稿导入轨道到当前草稿
   - 自动复制关联的素材
   - 支持时间偏移和重命名

5. **`inspect_material()`**：

   - 输出贴纸素材的 `resource_id`
   - 输出文字气泡的 `effect_id` 和 `resource_id`
   - 输出花字效果的 `resource_id`

  

#### 步骤 4.10：更新包入口

- Windows 平台：导出 `JianyingController`、`ExportResolution`、`ExportFramerate`
- 非 Windows 平台：跳过自动化相关导出
- 添加所有新类的导出
### 7.3 周期四验收标准

- [ ] 能够加载已有草稿作为模板
- [ ] 能够根据名称替换素材
- [ ] 能够根据片段替换素材（正确处理时长变化）
- [ ] 能够替换文本内容
- [ ] 能够从模板导入轨道到新草稿
- [ ] 能够提取模板中的贴纸/气泡/花字元数据
- [ ] （Windows）能够自动导出草稿为视频文件
- [ ] （Windows）能够设置导出分辨率和帧率

---

## 8. 开发周期五：高级特性与工程完善 

> **难度**：★★★★★ | **目标**：完善高级特性、向后兼容、代码质量、文档和发布

### 8.1 任务清单

| 序号   | 任务                    | 涉及文件                      |
| ---- | --------------------- | ------------------------- |
| 5.1  | 实现向后兼容的旧命名别名          | `__init__.py`             |
| 5.2  | 完善异常处理和边界条件           | 多个文件                      |
| 5.3  | 添加类型注解完善              | 多个文件                      |
| 5.4  | 编写完整的 README 文档       | `README.md`               |
| 5.5  | 准备 PyPI 发布材料          | `setup.py`, `MANIFEST.in` |
| 5.6  | 代码质量检查（flake8）        | `.flake8`                 |
| 5.7  | 添加 `.gitignore`       | `.gitignore`              |
| 5.8  | 准备 readme_assets 示例素材 | `readme_assets/`          |
| 5.9  | 编写完整的 demo.py         | `demo.py`                 |
| 5.10 | 跨平台兼容性测试              | 全部                        |

### 8.2 详细步骤

#### 步骤 5.1：实现向后兼容的旧命名别名

项目早期使用 snake_case 命名（如 `Script_file`、`Draft_folder`），后期统一改为 PascalCase（如 `ScriptFile`、`DraftFolder`）。需要保留旧命名的兼容：

1. **类别名**：使用 `__new__` 方法创建代理类，发出 `DeprecationWarning`
2. **枚举别名**：使用 `_DeprecatedEnum` 代理类，访问时发出警告


```python

class Script_file:
    """Deprecated: Use ScriptFile instead."""
    def __new__(cls, *args, **kwargs):
        _deprecated_class_warning("Script_file", "ScriptFile")
        return ScriptFile(*args, **kwargs)

```

#### 步骤 5.2：完善异常处理和边界条件

需要检查的边界条件：

- 素材时长不足时截取失败
- 片段重叠检测
- 轨道类型与片段类型不匹配
- 重复添加同类型特效/动画
- 模板模式下对不支持的操作给出明确提示
- 自动化导出超时处理
- 文件不存在时的错误提示
#### 步骤 5.3：添加类型注解完善

使用 `typing` 模块为所有公共方法添加类型注解：

- `Optional`、`Union`、`Literal`
- `List`、`Dict`、`Tuple`
- `TypeVar`、`Generic`
- `overload` 装饰器

#### 步骤 5.4：编写完整的 README 文档


README 应包含：

- 项目简介和使用思路图
- 功能清单（标注已实现/待实现）
- 安装说明（含跨平台兼容性说明）
- 快速上手教程
- 详细用法文档（模板模式、素材替换、文本替换等）
- 常见问题解答

#### 步骤 5.5：准备 PyPI 发布材料

- `setup.py`：完整的包配置
- `MANIFEST.in`：包含非 Python 文件
- `pypi_readme.md`：PyPI 页面描述
#### 步骤 5.6-5.7：代码质量和版本控制

- `.flake8`：配置代码风格检查
- `.gitignore`：排除不需要版本控制的文件

  

#### 步骤 5.8：准备示例素材


在 `readme_assets/tutorial/` 目录下准备：

- `audio.mp3`：示例音频
- `video.mp4`：示例视频
- `sticker.gif`：示例贴纸
- `subtitles.srt`：示例字幕

#### 步骤 5.9：编写完整的 demo.py

  

demo 应展示项目的核心功能：
1. 创建草稿
2. 添加音视频轨道
3. 创建音频片段（带淡入和音量调节）
4. 创建视频片段（带入场动画）
5. 创建贴纸片段（带背景填充）
6. 添加转场
7. 创建文本片段（带字体、颜色、气泡、花字、出场动画）
8. 保存草稿

#### 步骤 5.10：跨平台兼容性测试

- **Windows**：测试全部功能（草稿生成 + 模板模式 + 自动导出）
- **Linux/MacOS**：测试草稿生成和模板模式（自动导出不可用）
- 验证生成的草稿在 Windows 版剪映中能正确打开

### 8.3 周期五验收标准

- [ ] 旧命名别名正常工作并发出弃用警告
- [ ] 所有边界条件有合理的错误提示
- [ ] 类型注解覆盖所有公共 API
- [ ] README 文档完整清晰
- [ ] 可通过 `pip install` 安装
- [ ] 代码通过 flake8 检查
- [ ] demo.py 可正常运行并生成正确的草稿
- [ ] 跨平台兼容性验证通过

---

## 9. 操作方法与注意事项

### 9.1 基本操作流程

#### 9.1.1 创建草稿

```python

import pyJianYingDraft as draft

# 1. 指定剪映草稿文件夹路径（在剪映"全局设置 → 草稿位置"中查看）
draft_folder = draft.DraftFolder(r"你的草稿文件夹路径")

# 2. 创建新草稿（指定名称、分辨率、帧率）
script = draft_folder.create_draft(
    "我的草稿",      # 草稿名称
    1920, 1080,      # 分辨率（宽×高）
    fps=30,          # 帧率
    allow_replace=True  # 允许覆盖同名草稿
)

```

#### 9.1.2 添加轨道

```python

# 添加不同类型的轨道
script.add_track(draft.TrackType.audio)   # 音频轨道
script.add_track(draft.TrackType.video)   # 视频轨道
script.add_track(draft.TrackType.text)    # 文本轨道

# 同一类型可添加多条轨道（通过名称区分）
script.add_track(draft.TrackType.video, "画中画轨道", relative_index=1)

```

#### 9.1.3 创建和添加片段

```python

from pyJianYingDraft import trange

# 音频片段
audio_seg = draft.AudioSegment(
    "audio.mp3",                    # 素材路径
    trange("0s", "5s"),            # 时间范围（起始0s，持续5s）
    volume=0.6                      # 音量60%
)

audio_seg.add_fade("1s", "0s")     # 1秒淡入

# 视频片段
video_seg = draft.VideoSegment(
    "video.mp4",
    trange("0s", "4.2s")           # 取素材前4.2秒
)
video_seg.add_animation(draft.IntroType.斜切)  # 入场动画

# 文本片段
text_seg = draft.TextSegment(
    "你好，剪映！",
    video_seg.target_timerange,     # 与视频片段时间一致
    font=draft.FontType.文轩体,
    style=draft.TextStyle(color=(1.0, 1.0, 0.0)),  # 黄色
    clip_settings=draft.ClipSettings(transform_y=-0.8)  # 屏幕下方
)

  

# 添加到轨道
script.add_segment(audio_seg)
script.add_segment(video_seg)
script.add_segment(text_seg)

```

#### 9.1.4 保存草稿

```python
script.save()
```


然后在剪映中刷新草稿列表（可能需要进入再退出某个已有草稿，或重启剪映）。

### 9.2 模板模式操作

#### 9.2.1 加载模板

```python

# 方式一：直接加载已有草稿作为模板
script = draft_folder.load_template("已有草稿名称")

# 方式二：复制草稿并作为模板编辑
script = draft_folder.duplicate_as_template("模板草稿", "新草稿名称")

```

#### 9.2.2 替换素材

```python

# 根据名称替换（适合图片素材）
new_material = draft.AudioMaterial("新音频.mp3")
script.replace_material_by_name("旧音频.mp3", new_material)

# 根据片段替换（可重新指定截取范围）
audio_track = script.get_imported_track(draft.TrackType.audio, index=0)
script.replace_material_by_seg(
    audio_track, 0, new_material,
    source_timerange=trange("0s", "10s"),  # 截取前10秒
    handle_shrink=draft.ShrinkMode.cut_tail,
    handle_extend=draft.ExtendMode.push_tail
)

```

#### 9.2.3 提取素材元数据 

```python

# 提取贴纸、气泡、花字的 resource_id
draft_folder.inspect_material("草稿名称")

# 或
script.inspect_material()

```

### 9.3 自动化导出（仅 Windows）


```python

from pyJianYingDraft import JianyingController, ExportResolution, ExportFramerate

controller = JianyingController()
controller.export_draft(
    "草稿名称",
    output_path=r"C:\导出\视频.mp4",
    resolution=ExportResolution.RES_1080P,
    framerate=ExportFramerate.FR_30,
    timeout=1200  # 超时时间（秒）
)

```


### 9.4 重要注意事项

#### 9.4.1 版本兼容性

| 功能                          | 剪映版本要求           |     |
| --------------------------- | ---------------- | --- |
| 草稿生成（音视频/贴纸/文本/特效）          | 5.x 及以上所有版本 ✅    |     |
| 模板模式（加载 draft_content.json） | **仅 5.9 及以下** ⚠️ |     |
| 自动化导出                       | **仅 6.x 及以下** ⚠️ |     |

> ⚠️ 剪映 6+ 版本对 `draft_content.json` 进行了加密，模板模式暂不支持。剪映 7+ 版本隐藏了导出控件，自动化导出暂不支持。

#### 9.4.2 时间系统 

- **所有时间单位都是微秒（μs）**：1 秒 = 1,000,000 微秒
- `trange(start, duration)` 的第二个参数是**持续时长**，不是结束时间
- 使用 `tim("1s")` 将字符串转为微秒数

```python

# 正确：从 0s 开始，持续 5s（结束于 5s）
trange("0s", "5s")

# 错误理解：这不是"从 0s 到 5s"

```

#### 9.4.3 轨道规则

- **主视频轨道**（最底层的视频轨道）上的片段**必须从 0s 开始**，否则剪映会强制对齐
- 同一轨道上的片段**不能重叠**
- 特效/滤镜轨道在模板模式下**不可编辑**
#### 9.4.4 动画规则

- 视频片段：**组合动画**与**出入场动画**互斥，只能选其一
- 文本片段：若同时使用**循环动画**和**出入场动画**，必须先添加出入场动画，再添加循环动画
- 每种类型的动画只能添加一个
#### 9.4.5 转场规则

- 转场应添加在**前面的**片段上
- 每个片段只能有一个转场
#### 9.4.6 蒙版规则

- 每个片段只能有一个蒙版
- `rect_width` 和 `round_corner` 参数仅在蒙版类型为**矩形**时有效

#### 9.4.7 跨平台注意事项

- **Linux/MacOS**：支持草稿生成和模板模式，但**不支持自动导出**
- 生成的草稿**仍然需要在 Windows 版剪映下导出**
- `jianying_controller` 模块仅在 Windows 下可用

#### 9.4.8 素材路径

- 素材路径会以**绝对路径**写入 `draft_content.json`
- 如果素材文件被移动或删除，剪映中将无法找到素材
- 建议将素材放在固定位置，或使用相对路径（需自行处理）

#### 9.4.9 性能注意事项

- 大量关键帧会增加 JSON 文件大小和剪映加载时间
- `height_history` 等历史数据有上限（2000 条），超出会自动裁剪
- `telemetry_buffer` 也有大小限制

#### 9.4.10 调试技巧

- 生成的 `draft_content.json` 可以用文本编辑器打开查看
- 如果剪映无法识别草稿，检查 JSON 格式是否正确
- 可以先在剪映中手动创建一个简单草稿，导出其 JSON 作为参考
- 使用 `debug.log` 记录运行日志

---


> **文档版本**：v1.0  

> **生成日期**：2026-05-14  

> **适用项目版本**：pyJianYingDraft v0.2.6