# mason
mason agent ai，石匠铺子，python版本OpenClaw

# 开发周期

阶段一：MVP (最小可行性产品) —— “会说话的终端”

目标：打通 LangGraph 的基础循环，让 Agent 能在终端里接收输入并回复。

核心逻辑：实现一个最简单的 ReAct（Reason+Act）循环。

不包含：工具执行、沙箱、多模型切换、记忆持久化。

交付物：一个能通过 python main.py启动的 CLI 聊天机器人。

阶段二：工具集成 —— “赋予手脚”

目标：复刻 OpenClaw 的核心能力——调用 Shell 和 Python 代码。

核心逻辑：定义 Tool Schema，实现 LangChain Tools，并在 Graph 中加入 Tool Execution Node。

关键点：模拟 OpenClaw 的 !shell和 !python指令解析。

阶段三：沙箱与安全 —— “戴上镣铐”

目标：复刻 OpenClaw 的安全机制。

核心逻辑：引入 Docker 或 subprocess 隔离，实现 Permission Denied（权限拒绝）​ 和 Timeout（超时）​ 控制。

关键点：确保 Agent 不能随意删除系统文件。

阶段四：多智能体路由 —— “分派任务”

目标：复刻 OpenClaw 的 Router（路由器）。

核心逻辑：使用 LangGraph 的 Conditional Edges（条件边）。根据用户意图，将任务分发给不同的 Sub-Agent（如：Coding Agent vs Planning Agent）。

阶段五：记忆与上下文 —— “拥有大脑”

目标：实现长短期记忆。

核心逻辑：使用 LangChain 的 ConversationBufferMemory或 SummaryMemory，处理 Token 窗口限制。

阶段六：UI 与 API —— “穿上衣服”

目标：提供 Web UI 或 API 接口。

核心逻辑：封装 FastAPI，对接前端界面。