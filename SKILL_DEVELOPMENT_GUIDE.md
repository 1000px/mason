# Mason Skill 开发指南

> 本文档面向不熟悉 Mason 系统的开发者，阅读后即可独立开发一个合规的 Skill。

---

## 目录

1. [概述：什么是 Skill](#1-概述什么是-skill)
2. [Skill 的目录结构](#2-skill-的目录结构)
3. [文件详解](#3-文件详解)
   - [3.1 skill.yaml — 技能清单](#31-skillyaml--技能清单)
   - [3.2 SKILL.md — AI 指令文件](#32-skillmd--ai-指令文件)
   - [3.3 main.py — 技能实现](#33-mainpy--技能实现)
   - [3.4 __init__.py — 包标记](#34-__init__py--包标记)
4. [BaseSkill 基类详解](#4-baseskill-基类详解)
5. [渐进式披露设计](#5-渐进式披露设计)
6. [完整示例：从零开发一个 Skill](#6-完整示例从零开发一个-skill)
7. [Skill 的加载机制](#7-skill-的加载机制)
8. [内置 Skill vs 用户 Skill](#8-内置-skill-vs-用户-skill)
9. [常见问题](#9-常见问题)

---

## 1. 概述：什么是 Skill

Skill 是 Mason 系统中**可被 AI 调用的功能单元**。每个 Skill 封装了一个具体的操作能力（如查询天气、发送邮件、设置提醒），AI 在对话中根据用户意图自动选择合适的 Skill 并调用它。

Skill 的设计遵循 **Anthropic Skill 最佳实践**，核心理念是**渐进式披露**——AI 先看到简短描述，需要时才加载完整指令。

### Skill 的生命周期

```
加载阶段                运行阶段                 卸载阶段
────────              ────────               ────────
validate()  →  setup()  →  execute()  →  teardown()
  校验         初始化        执行           清理
```

---

## 2. Skill 的目录结构

每个 Skill 是一个独立的目录，放在 `src/skills/builtin/`（内置）或 `src/skills/user/`（用户安装）下。

### 命名规范

- 目录名使用 **kebab-case**（小写字母 + 连字符），如 `email-sender`、`news-fetcher`
- Skill 的 `name` 字段使用 **snake_case**（小写字母 + 下划线），如 `email_sender`、`news_fetcher`

### 标准目录结构

```
src/skills/builtin/<skill-name>/
├── skill.yaml          # 技能清单（必需）
├── SKILL.md            # AI 指令文件（必需）
├── main.py             # 技能实现（必需）
├── __init__.py         # 包标记（必需，可为空文件）
├── scripts/            # 脚本文件（可选）
│   └── helper.py
├── references/         # 参考文档（可选）
│   └── api-doc.md
└── assets/             # 静态资源（可选）
    └── template.html
```

---

## 3. 文件详解

### 3.1 skill.yaml — 技能清单

这是 Skill 的**元数据文件**，系统加载 Skill 时首先读取它。

```yaml
name: weather                    # Skill 唯一标识（snake_case）
version: "1.0.0"                 # 语义化版本号
author: Mason Team               # 作者
entry_point: main.py             # 入口文件（默认 main.py）
permissions:                     # 权限声明
  network: true                  # 是否需要网络访问
  filesystem: false              # 是否需要文件系统访问
  max_cpu: 0.5                   # CPU 限制（核心数）
  max_memory: 128                # 内存限制（MB）
```

**字段说明**：

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | ✅ | Skill 唯一标识，snake_case，与目录名对应 |
| `version` | ✅ | 语义化版本号 |
| `author` | 推荐 | 作者信息 |
| `entry_point` | 否 | 入口 Python 文件，默认 `main.py` |
| `permissions` | 推荐 | 权限声明，用于安全沙箱控制 |

---

### 3.2 SKILL.md — AI 指令文件

这是 Skill 的**核心文件**，AI 在决定是否调用以及如何调用 Skill 时参考它。

SKILL.md 采用 **YAML 前置元数据 + Markdown 正文** 的格式：

``````markdown
---
name: weather
description: |
  查询全球城市的实时天气信息（温度、天气状况）。
  当用户询问某地天气、气温预报、穿衣建议，或提到"天气"+"城市名"时激活。
version: "1.0.0"
author: Mason Team
---

# 天气查询

## 激活条件
- 用户询问"今天天气怎么样"、"北京多少度"、"需要带伞吗"
- 用户提到具体城市名称 + 天气相关词汇

## 核心规则
- 必须指定城市名称，若用户未提供则主动询问
- 返回实时天气数据，绝不编造或猜测
- 输出简洁明了，包含天气状况和温度

## 执行流程
1. 从用户消息中解析城市名称
2. 调用 weather skill 获取该城市的实时天气数据
3. 将结果以自然语言回复用户

## 输出模板
```
{city} 天气：{weather_condition}，温度 {temperature}℃
```
``````

#### YAML 前置元数据

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | ✅ | 与 skill.yaml 中的 name 一致 |
| `description` | ✅ | **最关键字段**。描述 Skill 做什么 + 何时触发。AI 根据此字段决定是否调用 |
| `version` | 推荐 | 版本号 |
| `author` | 推荐 | 作者 |

#### description 编写要点

`description` 是 AI 判断是否调用 Skill 的**唯一依据**，必须包含两部分：

1. **做什么**：Skill 的功能描述
2. **何时触发**：用户说什么话时应该激活

```yaml
# ✅ 好的 description
description: |
  查询全球城市的实时天气信息（温度、天气状况）。
  当用户询问某地天气、气温预报、穿衣建议，或提到"天气"+"城市名"时激活。

# ❌ 不好的 description（缺少触发条件）
description: 查询天气信息。

# ❌ 不好的 description（缺少功能描述）
description: 当用户问天气时使用。
```

#### Markdown 正文

正文是 AI 决定调用 Skill 后加载的**完整指令**，应包含：

- **激活条件**：更详细的触发场景
- **核心规则**：执行时必须遵守的约束
- **执行流程**：分步骤的操作指南
- **输出模板**：期望的输出格式

---

### 3.3 main.py — 技能实现

这是 Skill 的**代码实现**，必须包含一个继承自 `BaseSkill` 的类。

#### 最小实现

```python
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field


class MySkillParams(BaseModel):
    """定义 Skill 的输入参数"""
    query: str = Field(description="用户查询内容")


class MySkill(BaseSkill):
    name = "my_skill"                              # 与 skill.yaml 一致
    description = "技能描述，说明做什么和何时触发"    # 与 SKILL.md 一致
    args_schema = MySkillParams                     # 参数模型
    permissions = {                                 # 权限声明
        "network": False,
        "filesystem": False,
        "max_cpu": 0.1,
        "max_memory": 32,
    }

    def execute(self, query: str) -> str:
        """核心执行逻辑，返回字符串结果"""
        return f"处理结果: {query}"
```

#### 关键要点

1. **类名**：任意，但必须是 `BaseSkill` 的子类
2. **name**：必须与 `skill.yaml` 和 `SKILL.md` 中的 name 一致
3. **description**：与 `SKILL.md` 的 description 一致
4. **args_schema**：一个 Pydantic `BaseModel`，定义 AI 调用时需要传入的参数
5. **execute()**：核心方法，接收参数，返回字符串结果

#### 参数定义（args_schema）

使用 Pydantic 的 `BaseModel` + `Field` 定义参数：

```python
from pydantic import BaseModel, Field

class EmailParams(BaseModel):
    to: str = Field(description="收件人邮箱地址")
    subject: str = Field(description="邮件主题")
    body: str = Field(description="邮件正文内容")
    cc: str = Field(default="", description="抄送邮箱地址（可选）")
```

- 每个字段的 `description` 会传给 AI，帮助 AI 正确填参
- 可选参数设置 `default` 值
- 必需参数不设 `default`

---

### 3.4 __init__.py — 包标记

空文件即可，用于标记该目录为 Python 包。

---

## 4. BaseSkill 基类详解

```python
class BaseSkill(ABC):
    name: str = "base_skill"                        # Skill 名称
    description: str = "A base skill."              # Skill 描述
    args_schema: Optional[Type[BaseModel]] = None   # 参数模型

    permissions: Dict[str, Any] = {                 # 权限声明
        "network": False,
        "filesystem": False,
        "max_cpu": 0.5,
        "max_memory": 128,
    }

    def validate(self) -> bool:                     # 校验：加载时调用
        ...

    def setup(self) -> None:                        # 初始化：校验通过后调用
        ...

    def teardown(self) -> None:                     # 清理：卸载或 reload 时调用
        ...

    @abstractmethod
    def execute(self, **kwargs) -> str:             # 执行：AI 调用时触发
        ...

    def get_schema(self) -> Dict[str, Any]:         # 生成 OpenAI function calling schema
        ...
```

### 生命周期钩子

| 钩子 | 调用时机 | 用途 |
|------|----------|------|
| `validate()` | Skill 加载时 | 校验配置是否合法，返回 `False` 则跳过加载 |
| `setup()` | 校验通过后 | 初始化资源（如数据库连接、API 客户端） |
| `execute()` | AI 调用时 | 核心业务逻辑 |
| `teardown()` | 卸载或 reload 时 | 释放资源、清理状态 |

### 覆写 validate()

```python
def validate(self) -> bool:
    if not self.name or self.name == "base_skill":
        return False
    if not self.description:
        return False
    return True
```

### 覆写 setup() / teardown()

```python
def setup(self) -> None:
    self.client = SomeAPIClient(api_key=os.getenv("API_KEY"))

def teardown(self) -> None:
    self.client.close()
```

---

## 5. 渐进式披露设计

Mason 的 Skill 系统采用**三级渐进式披露**，避免一次性把所有信息塞给 AI：

```
Level 1: description 字段（始终在上下文中）
  ↓ AI 决定调用后
Level 2: SKILL.md 正文（加载到上下文）
  ↓ 需要更多细节时
Level 3: scripts/ references/ assets/（按需加载）
```

### 设计原则

1. **description 要精准**：让 AI 在正确的时机调用正确的 Skill
2. **SKILL.md 要完整**：包含所有执行规则和约束
3. **大文件外置**：脚本、参考文档放在子目录，AI 按需读取

---

## 6. 完整示例：从零开发一个 Skill

以开发一个"随机笑话" Skill 为例。

### Step 1：创建目录

```bash
mkdir -p src/skills/builtin/joke-teller
```

### Step 2：编写 skill.yaml

```yaml
name: joke_teller
version: "1.0.0"
author: Your Name
entry_point: main.py
permissions:
  network: true
  filesystem: false
  max_cpu: 0.1
  max_memory: 32
```

### Step 3：编写 SKILL.md

```markdown
---
name: joke_teller
description: |
  讲一个随机笑话。
  当用户说"讲个笑话"、"来个段子"、"说个好笑的笑话"、"幽默一下"时激活。
version: "1.0.0"
author: Your Name
---

# 随机笑话

## 激活条件
- 用户说"讲个笑话"、"来个段子"、"说个笑话"
- 用户说"幽默一下"、"开心一下"
- 用户表达想听笑话的意图

## 核心规则
- 每次调用返回一个随机笑话
- 笑话应健康、不涉及政治和敏感话题
- 直接输出笑话内容，不需要额外评论

## 执行流程
1. 调用 joke_teller skill 获取随机笑话
2. 将笑话直接输出给用户

## 输出模板
```
{笑话内容}
```
```

### Step 4：编写 main.py

```python
import random
from src.skills.base import BaseSkill
from pydantic import BaseModel


class JokeTellerParams(BaseModel):
    pass


JOKES = [
    "为什么程序员不喜欢出门？因为外面没有 Debug 模式。",
    "一个 SQL 语句走进酒吧，看到两张表，它问：'我可以 JOIN 你们吗？'",
    "程序员最讨厌的数字是什么？1024。因为 1024 = 1G（一级），而程序员都想当架构师。",
    "产品经理：这个需求很简单。程序员：那你来写。",
]


class JokeTellerSkill(BaseSkill):
    name = "joke_teller"
    description = "讲一个随机笑话。当用户说'讲个笑话'、'来个段子'、'幽默一下'时激活。"
    args_schema = JokeTellerParams
    permissions = {"network": False, "filesystem": False, "max_cpu": 0.1, "max_memory": 32}

    def execute(self) -> str:
        return random.choice(JOKES)
```

### Step 5：创建 __init__.py

```bash
touch src/skills/builtin/joke-teller/__init__.py
```

### Step 6：重启 Mason 测试

重启 Mason，输入"讲个笑话"，AI 会自动调用 `joke_teller` Skill。

---

## 7. Skill 的加载机制

### 加载流程

```
SkillLoader.__init__()
  → _load_all()
    → 扫描 builtin/ 和 user/ 目录
      → 找到 skill.yaml → 读取元数据
        → 找到 main.py → import 模块
          → 查找 BaseSkill 子类 → 实例化
            → 注入 permissions
              → validate() → 校验
                → setup() → 初始化
                  → 注册到 _skills 字典
```

### 关键规则

1. 目录下必须有 `skill.yaml`，否则跳过
2. `skill.yaml` 中必须有 `name` 字段
3. `main.py` 中必须有且仅有一个 `BaseSkill` 的子类
4. `validate()` 返回 `False` 则跳过加载
5. 加载失败只记录日志，不影响其他 Skill

### 双目录机制

- `builtin/`：系统内置 Skill，随项目分发
- `user/`：用户通过 `install_skill.py` 安装的 Skill
- `user/` 中的同名 Skill 不会覆盖 `builtin/`（先扫描到的优先）

---

## 8. 内置 Skill vs 用户 Skill

| | 内置 Skill | 用户 Skill |
|------|------------|------------|
| 目录 | `src/skills/builtin/` | `src/skills/user/` |
| 来源 | 随项目分发 | 通过 `install_skill.py` 安装 |
| 版本管理 | Git 管理 | 独立管理 |
| 卸载 | 手动删除 | `uninstall_skill.py` |

### 安装用户 Skill

```bash
python install_skill.py <source_path>

# 示例
python install_skill.py https://github.com/user/weather-skill/archive/main.zip
python install_skill.py D:/my-skills/custom-skill
```

### 卸载用户 Skill

```bash
python uninstall_skill.py <skill_name>

# 示例
python uninstall_skill.py custom_skill
```

---

## 9. 常见问题

### Q: Skill 加载失败怎么办？

查看终端日志，搜索 `ERROR:src.skills.loader`。常见原因：
- `skill.yaml` 缺少 `name` 字段
- `main.py` 中没有 `BaseSkill` 子类
- `main.py` 有语法错误
- `name` 在三个文件中不一致

### Q: AI 不调用我的 Skill？

检查 `SKILL.md` 的 `description` 字段：
- 是否包含"做什么"和"何时触发"两部分？
- 触发关键词是否覆盖了用户的表达方式？

### Q: execute() 的返回值太长怎么办？

返回值会作为 `ToolMessage` 传给 AI，建议控制在 2000 字符以内。大量数据可以写入文件，返回文件路径。

### Q: Skill 之间可以互相调用吗？

不推荐。Skill 应保持独立。如需共享逻辑，抽取到 `src/` 下的公共模块。

### Q: 如何让 Skill 的输出不被 AI 二次格式化？

在 `SKILL.md` 的核心规则中明确写：
```
- 直接将工具返回的结果原样输出给用户，不要添加任何额外格式或评论
```

---

## 附录：现有 Skill 参考

| Skill | 目录 | 特点 |
|-------|------|------|
| weather | `builtin/weather/` | 网络 API 调用 |
| reminder | `builtin/reminder/` | 定时任务 + MySQL 持久化 |
| cancel-reminder | `builtin/cancel-reminder/` | 跨 Skill 协作（调用 SchedulerManager） |
| list-reminders | `builtin/list-reminders/` | 数据库查询 + 透传输出 |
| email-sender | `builtin/email-sender/` | SMTP 邮件发送 |
| news-fetcher | `builtin/news-fetcher/` | 脚本外置到 scripts/ 目录 |