# 创建专用的Dockerfile（安全加固）
我们需要构建一个 “最小化、无特权”​ 的 Docker 镜像。不要用你之前的 python:3.11-slim直接跑 Skill，那还不够安全。
在项目根目录创建 Dockerfile.skill：
```docker
# Dockerfile.skill
FROM python:3.11-slim

# 1. 创建非 root 用户（防止提权攻击）
RUN addgroup --system app && adduser --system --group app

# 2. 设置工作目录（容器内的安全区）
WORKDIR /workspace

# 3. 安装必要的依赖（仅基础工具，不装 sudo）
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# 4. 切换到非 root 用户
USER app

# 5. 设置环境变量
ENV PATH="/home/app/.local/bin:$PATH"

# 6. 默认命令（挂起，等待命令注入）
CMD ["tail", "-f", "/dev/null"]
```

构建这个镜像，只需要一次
```bash
docker build -f Dockerfile.skill -t mason-skill-sandbox .
```