# HeadroomWebUI

Headroom 代理的本地 Web 配置中心与监控看板。

[Headroom](https://github.com/chopratejas/headroom) 是一个 Claude Code 上下文压缩代理，位于 Claude Code 与 API 后端之间，通过智能压缩减少 token 消耗、降低延迟和成本。

**没有 WebUI 之前：**
- Headroom 只有 CLI 参数，每次改配置都要敲一长串 `docker run ...` 命令
- 想看压缩效果？敲 `curl http://localhost:8787/stats` 看 JSON
- 想切换 Claude Code 路由？手动改配置文件
- 想看日志？`docker logs headroom`

**有了 WebUI：**
- 📊 实时看板 — 压缩率、节省 tokens、请求健康、延迟一目了然
- ⚙️ 可视化配置 — 表单填写参数，一键保存并自动重启容器
- 🔀 一键切换路由 — 「Headroom 代理」↔「直连 DeepSeek」
- 📋 在线日志 — 自带高亮和下载

## 快速启动

### 第一步：检查环境

打开终端（cmd / PowerShell），依次确认：

```bash
# 1. Python 装了没
python --version
# 应该输出 Python 3.12+

# 如果提示找不到 Python，但你装了 Anaconda，试试：
conda activate base
python --version
```

如果没有 Python 也没有 Anaconda，去安装其中一个：
- [Python 3.12+](https://www.python.org/downloads/)（轻量）
- [Anaconda](https://www.anaconda.com/download) 或 [Miniconda](https://docs.anaconda.com/miniconda/)（科学计算用户常用）

```bash
# 2. Docker 装了没
docker ps
# 应该输出容器列表（或空列表），而不是报错
```

如果没有，去安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

### 第二步：启动 Headroom 容器

WebUI 是管理 Headroom 的，所以 Headroom 本身要先跑起来：

```bash
docker run -d --name headroom --restart unless-stopped -p 8787:8787 ghcr.io/chopratejas/headroom:latest
```

> 第一次运行会自动拉取镜像。启动后访问 `http://localhost:8787/health` 应该返回 `{"status":"healthy"}`。

### 第三步：克隆并启动 WebUI

```bash
# 克隆仓库
git clone https://github.com/diyu331/HeadroomWebUI.git
cd HeadroomWebUI
```

**方式 A：pip + venv（推荐，轻量）**
```bash
# 创建虚拟环境
python -m venv venv
# Windows 激活:
venv\Scripts\activate
# macOS / Linux 激活:
# source venv/bin/activate

# 安装依赖
pip install flask requests

# 启动
python app.py
```

**方式 B：conda / miniconda（如果你在用 Anaconda）**
```bash
# 创建虚拟环境（指定 Python 版本）
conda create -n headroom-webui python=3.12 -y
conda activate headroom-webui

# 安装依赖
pip install flask requests

# 启动
python app.py
```

浏览器打开 `http://localhost:5000`，正常就能看到看板了。

> **Windows 用户也可以直接双击 `start.bat`**，效果同上。

### 第四步：把 Claude Code 路由到 Headroom

在看板中打开 **配置 → 系统环境配置**，点击 **Headroom 代理** 按钮，保存。

然后在 Claude Code 的配置文件中（`~\.claude\settings.json`），`ANTHROPIC_BASE_URL` 会自动更新为 `http://localhost:8787`。

> 已有 Claude Code 会话需要退出重启。新会话的请求就会经过 Headroom 压缩了。

## 功能说明

### 状态看板

四张卡片实时展示：

| 卡片 | 内容 |
|------|------|
| 运行状态 | 容器是否健康、运行了多久、版本号 |
| 压缩统计 | 总共节省了多少 tokens、压缩率、压缩前后对比 |
| 请求健康 | 成功率、缓存命中、失败数、限流数 |
| 请求概览 | 总请求数、平均延迟 |

页面下方还有压缩策略分布图和按模型拆分的压缩明细。

### 配置中心

**系统环境配置** — 切换 Claude Code 的路由（代理或直连），自动写入配置文件。

**Headroom 参数** — 按分类展示所有参数（运行模式、优化开关、记忆、后端、日志等），修改后一键保存并自动重建容器。

**配置快照** — 显示当前容器的启动命令和环境变量，方便复盘。

### 日志

实时查看 Headroom 容器日志，WARN 和 ERROR 会高亮显示，支持下载。

## 工作原理

```
你操作浏览器 (localhost:5000)
      │
      ▼
   Flask 后端 (app.py)
      │
      ├── 读取/写入 ~\.claude\settings.json（路由配置）
      ├── 调用 Docker CLI 控制 Headroom 容器
      └── 调用 Headroom API (localhost:8787) 获取统计数据
```

| 技术 | 用途 |
|------|------|
| Python + Flask | 后端 API |
| Tailwind CSS + 原生 JS | 前端界面 |
| Docker CLI | 容器启停和重建 |
| settings.json / profile.ps1 | 配置持久化 |

## Docker 路径自定义

如果 `docker` 命令不在系统 PATH 中（比如 Docker Desktop 安装路径特殊），可以在 WebUI 配置页面的「系统环境配置」中填写 docker.exe 的完整路径。

例如你的 Docker 安装路径可能是 `C:\Program Files\Docker\Docker\resources\bin\docker.exe`，实际位置以你电脑为准。

或者设置环境变量：

```bash
set DOCKER_PATH=C:\你的实际路径\docker.exe
```

## 常见问题

**Q: 看板上全是 0？**
A: 说明还没有 Claude Code 请求经过 Headroom。确认 Claude Code 的 `ANTHROPIC_BASE_URL` 已设为 `http://localhost:8787`，然后新开一个窗口用 Claude Code 发条消息。

**Q: 修改 Headroom 参数后容器没重启？**
A: 检查 Docker Desktop 是否在运行。WebUI 会执行 `docker stop → rm → run`，Docker 不可用时无法重建。

**Q: 怎么关掉？**
A: 关掉运行 `python app.py` 的终端窗口就行。Headroom 容器不受影响，下次启动 WebUI 还会连上。

## 修改记录

- 2026-06-05: 初始版本
