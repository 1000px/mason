# Mason

> 🦖 Mason Agent AI Studio — Python 版 AI Agent 框架，支持 CLI 终端交互与 Web UI。

Mason 是一个基于 **LangGraph** 构建的多智能体 AI 助手框架。它采用**路由器 + 子 Agent** 架构，根据用户意图自动将任务分发给 General Agent（通用对话）或 Coder Agent（编程任务），并通过可插拔的 **Skill 系统**扩展 AI 的能力边界。

---

## 目录

- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [内置 Skill](#内置-skill)
- [Skill 开发](#skill-开发)
- [Web UI](#web-ui)
- [技术栈](#技术栈)

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **多智能体路由** | 根据用户意图自动分发到 General Agent 或 Coder Agent |
| **Skill 插件系统** | 遵循 Anthropic Skill 最佳实践，支持渐进式披露、生命周期钩子、权限声明 |
| **定时任务** | 基于 MySQL 持久化的定时提醒，重启后自动恢复 |
| **长短期记忆** | MySQL 持久化的 Checkpointer（短期）+ Store（长期用户画像） |
| **Docker 沙箱** | 代码执行隔离，支持超时和权限控制 |
| **多 LLM 支持** | DeepSeek / Qwen / NVIDIA，通过 `.env` 一键切换 |
| **双界面** | CLI 终端 + Web UI（FastAPI + WebSocket 流式输出） |
| **流式输出** | 实时逐字输出 AI 回复 |

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                    main.py                       │
│  ┌──────────────┐    ┌──────────────────────┐   │
│  │ input_thread  │───▶│     TASK_QUEUE        │   │
│  │  (用户输入)    │    │  (统一消息队列)        │   │
│  └──────────────┘    └──────────┬───────────┘   │
│                                 │                │
│                    ┌────────────▼───────────┐   │
│                    │     主循环处理           │   │
│                    └────────────┬───────────┘   │
│                                 │                │
│              ┌──────────────────▼──────────────┐ │
│              │         LangGraph                │ │
│              │  ┌──────────────────────────┐   │ │
│              │  │        Router             │   │ │
│              │  │   (关键词规则路由)         │   │ │
│              │  └──────┬──────────┬────────┘   │ │
│              │         │          │             │ │
│              │  ┌──────▼──┐  ┌───▼──────┐      │ │
│              │  │ General  │  │  Coder   │      │ │
│              │  │  Agent   │  │  Agent   │      │ │
│              │  │ + Skills │  │ + Tools  │      │ │
│              │  └────┬─────┘  └────┬─────┘      │ │
│              │       │             │             │ │
│              │  ┌────▼─────────────▼────┐       │ │
│              │  │     Tool Executor     │       │ │
│              │  │  (Skill / Tool 调度)  │       │ │
│              │  └──────────────────────┘       │ │
│              └─────────────────────────────────┘ │
│                                 │                │
│  ┌──────────────────────────────▼──────────────┐ │
│  │              MySQL                           │ │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │ │
│  │  │Checkpoint│ │  Store   │ │Scheduled     │ │ │
│  │  │ (短期记忆)│ │(长期记忆)│ │Tasks (定时)  │ │ │
│  │  └──────────┘ └──────────┘ └─────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 请求处理流程

```
用户输入 → TASK_QUEUE → 主循环
  ├── 普通消息 → extract_memory → LangGraph → 流式输出
  └── 定时触发 → SchedulerManager._trigger → TASK_QUEUE → LangGraph
```

### Agent 路由规则

| 关键词 | 分发目标 | 可用工具 |
|--------|----------|----------|
| 代码、编程、debug、函数、算法、python、shell | Coder Agent | `execute_shell`、`execute_python` |
| 其他 | General Agent | 所有已加载的 Skill |

---

## 项目结构

```
mason/
├── src/
│   ├── main.py                  # CLI 入口，主循环 + 消息队列
│   ├── agents/                  # Agent 定义
│   │   ├── base.py              # BaseAgent 基类
│   │   ├── general.py           # General Agent（通用对话）
│   │   └── coder.py             # Coder Agent（编程任务）
│   ├── config/
│   │   └── settings.py          # 配置管理（环境变量读取）
│   ├── db/
│   │   ├── memory.py            # MySQL 连接 + Checkpointer + Store
│   │   └── task_store.py        # 定时任务 CRUD（scheduled_tasks 表）
│   ├── graph/
│   │   ├── builder.py           # LangGraph 图构建
│   │   ├── nodes.py             # 图节点（router / agent / tools）
│   │   └── state.py             # 图状态定义（MasonState）
│   ├── llm/
│   │   └── provider.py          # LLM 提供商工厂（DeepSeek / Qwen / NVIDIA）
│   ├── sandbox/
│   │   ├── base.py              # BaseSandbox 抽象类
│   │   ├── docker_sandbox.py    # Docker 沙箱实现
│   │   └── local_sandbox.py     # 本地沙箱（开发用）
│   ├── skills/
│   │   ├── base.py              # BaseSkill 基类（生命周期 + schema 生成）
│   │   ├── loader.py            # SkillLoader（扫描、加载、注册）
│   │   ├── skill_template.yaml  # Skill 模板
│   │   ├── builtin/             # 内置 Skill
│   │   │   ├── weather/         # 天气查询
│   │   │   ├── reminder/        # 定时提醒
│   │   │   ├── cancel-reminder/ # 取消提醒
│   │   │   ├── list-reminders/  # 列出提醒
│   │   │   ├── email-sender/    # 邮件发送
│   │   │   └── news-fetcher/    # 新闻抓取
│   │   └── user/                # 用户安装的 Skill
│   ├── tools/
│   │   ├── base.py              # BaseTool 基类
│   │   ├── shell.py             # Shell 命令执行
│   │   └── python.py            # Python 代码执行
│   └── web/
│       ├── app.py               # FastAPI + WebSocket 服务
│       ├── static/              # 静态资源
│       └── templates/           # HTML 模板
├── install_skill.py             # Skill 安装脚本
├── uninstall_skill.py           # Skill 卸载脚本
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
├── SKILL_DEVELOPMENT_GUIDE.md   # Skill 开发指南
└── README.md                    # 本文件
```

---

## 快速开始

### 环境要求

- Python 3.11+
- MySQL 8.0+
- Docker（可选，用于沙箱隔离）

### 1. 克隆项目

```bash
git clone <repo-url>
cd mason
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入必要配置：

```env
# LLM 提供商（deepseek / qwen / nvidia）
ACTIVE_MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key_here

# MySQL 连接
HOST=localhost
PORT=3306
USER=root
PASSWORD=your_password
DATABASE=mason
```

### 4. 启动 CLI

```bash
python -m src.main
```

启动后看到：

```
🦖 Mason Agent's AI Studio Working ...

✅ Reminder 队列注入成功！
✅ [Reminder] 任务队列已连接。
----------------------------------------
💡 提示：输入 'exit' 退出。
💡 定时任务触发时，会自动在此处执行。
----------------------------------------
You:
```

### 5. 启动 Web UI（可选）

```bash
python -m src.web.app
```

访问 `http://localhost:8080`

---

## 配置说明

### LLM 提供商

| 提供商 | 环境变量 | 默认模型 |
|--------|----------|----------|
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| Qwen（通义千问） | `DASHSCOPE_API_KEY` | `qwen-plus` |
| NVIDIA | `NVIDIA_API_KEY` | `deepseek-ai/deepseek-v4-pro` |

通过 `ACTIVE_MODEL_PROVIDER` 切换。

### MySQL 数据库

Mason 使用 MySQL 存储三类数据：

| 用途 | 表 / 机制 | 说明 |
|------|-----------|------|
| 短期记忆 | LangGraph Checkpointer | 对话历史，支持多轮上下文 |
| 长期记忆 | LangGraph Store | 用户画像（姓名、偏好等） |
| 定时任务 | `scheduled_tasks` 表 | 自动建表，持久化定时提醒 |

### 沙箱配置

```env
SANDBOX_TYPE=docker        # docker 或 local
SANDBOX_TIMEOUT=10         # 超时秒数
```

---

## 内置 Skill

| Skill | 功能 | 触发示例 |
|-------|------|----------|
| `weather` | 查询城市实时天气 | "北京今天天气怎么样" |
| `reminder` | 设置定时提醒（MySQL 持久化） | "5分钟后提醒我开会" |
| `cancel-reminder` | 取消定时提醒 | "取消任务 abc12345" |
| `list-reminders` | 列出所有待执行提醒 | "列出当前定时任务" |
| `email-sender` | 发送电子邮件 | "给 boss@example.com 发邮件" |
| `news-fetcher` | 抓取 V2EX 科技新闻 | "抓取最新5条科技新闻" |

---

## Skill 开发

Mason 的 Skill 系统遵循 **Anthropic Skill 最佳实践**，支持渐进式披露、生命周期管理和权限声明。

### 快速创建 Skill

每个 Skill 是一个独立目录，包含 4 个文件：

```
src/skills/builtin/<skill-name>/
├── skill.yaml      # 元数据
├── SKILL.md        # AI 指令
├── main.py         # 实现代码
└── __init__.py     # 包标记（空文件）
```

### 最小示例

**skill.yaml**
```yaml
name: my_skill
version: "1.0.0"
author: Your Name
permissions:
  network: false
  filesystem: false
```

**SKILL.md**
```markdown
---
name: my_skill
description: |
  我的自定义功能。当用户说"触发关键词"时激活。
---

# 我的 Skill

## 核心规则
- 直接将工具返回的结果输出给用户
```

**main.py**
```python
from src.skills.base import BaseSkill
from pydantic import BaseModel

class MyParams(BaseModel):
    pass

class MySkill(BaseSkill):
    name = "my_skill"
    description = "我的自定义功能。当用户说'触发关键词'时激活。"
    args_schema = MyParams

    def execute(self) -> str:
        return "Hello from my skill!"
```

详细开发指南请参阅 [SKILL_DEVELOPMENT_GUIDE.md](SKILL_DEVELOPMENT_GUIDE.md)。

---

## Web UI

Mason 提供基于 FastAPI + WebSocket 的 Web 界面，支持流式对话。

```bash
python -m src.web.app
```

特性：
- 实时流式输出 AI 回复
- 多客户端独立会话
- 自动记忆提取

---

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | LangGraph 1.0+ |
| LLM 接入 | LangChain + ChatOpenAI |
| 记忆存储 | LangGraph Checkpointer (MySQL) + Store (MySQL) |
| Web 服务 | FastAPI + WebSocket + Jinja2 |
| 沙箱隔离 | Docker SDK for Python |
| 参数校验 | Pydantic 2.x |
| 配置管理 | python-dotenv |
| 时间解析 | dateparser |
| 数据库驱动 | PyMySQL + aiomysql |

---

## License

MIT