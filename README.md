# Headroom Dashboard

[**English**](#english) · [**中文**](#chinese)

---

<h2 id="english">English</h2>

Local web dashboard for managing the [Headroom](https://github.com/chopratejas/headroom) proxy — a context compression layer for Claude Code that sits between the client and your API backend, reducing token consumption, latency, and cost.

**Before HeadroomWebUI:**
- Headroom runs entirely through CLI flags — every config change means typing a long `docker run ...` command
- Want to check compression stats? `curl http://localhost:8787/stats` and read raw JSON
- Switch Claude Code routing? Manually edit config files
- Check logs? `docker logs headroom`

**With HeadroomWebUI:**
- 📊 **Dashboard** — compression ratio, tokens saved, request health, latency at a glance
- ⚙️ **Visual config** — edit Headroom parameters through a form, save and auto-rebuild the container
- 🔀 **One-click routing** — toggle Claude Code between "via Headroom proxy" and "direct to DeepSeek"
- 📋 **Built-in log viewer** — syntax-highlighted, one-click download

### Quick Start

#### 1. Prerequisites

Open a terminal and check:

```bash
# Python 3.12+
python --version

# If `python` is not found but you use Anaconda:
conda activate base
python --version

# Docker (Docker Desktop must be running)
docker ps
```

If missing, install:
- [Python 3.12+](https://www.python.org/downloads/) or [Miniconda](https://docs.anaconda.com/miniconda/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

#### 2. Start the Headroom container

```bash
docker run -d --name headroom --restart unless-stopped -p 8787:8787 ghcr.io/chopratejas/headroom:latest
```

> The image will be pulled automatically on first run. Visit `http://localhost:8787/health` to verify — you should see `{"status":"healthy"}`.

#### 3. Clone and start the WebUI

```bash
git clone https://github.com/diyu331/HeadroomWebUI.git
cd HeadroomWebUI
```

**Option A: pip + venv (lightweight)**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
# source venv/bin/activate

pip install flask requests
python app.py
```

**Option B: conda**
```bash
conda create -n headroom-webui python=3.12 -y
conda activate headroom-webui
pip install flask requests
python app.py
```

Open `http://localhost:5000` in your browser.

> **Windows users:** You can also double-click `start.bat`.

#### 4. Route Claude Code through Headroom

Open the WebUI → **Config → System Config**, click the **Headroom proxy** button, and save.

Claude Code's `~\.claude\settings.json` will be updated automatically. Start a new Claude Code session — all requests will now flow through Headroom.

### Feature Overview

| Dashboard Card | Shows |
|---------------|-------|
| Status | Container health, uptime, version |
| Compression | Tokens saved, ratio, before/after comparison |
| Request Health | Success rate, cache hits, failures, rate limits |
| Overview | Total requests, avg latency, compression cache hit rate |

**Config center:** Edit system routing, Headroom parameters (mode, optimization, memory, backend, logging), and view config snapshots.

**Log viewer:** Real-time container logs with WARN/ERROR highlighting and download.

### Architecture

```
Your browser (localhost:5000)
      │
      ▼
   Flask backend (app.py)
      │
      ├── reads/writes ~\.claude\settings.json (routing config)
      ├── calls Docker CLI to manage the Headroom container
      └── fetches stats from Headroom API (localhost:8787)
```

| Tech | Role |
|------|------|
| Python + Flask | Backend API |
| Tailwind CSS + vanilla JS | Frontend |
| Docker CLI | Container lifecycle |
| settings.json / profile.ps1 | Config persistence |

### Custom Docker Path

If `docker` is not in your system PATH, go to the WebUI **Config → System Config** page and enter the full path to `docker.exe`, or set an environment variable:

```bash
set DOCKER_PATH=C:\path\to\your\docker.exe
```

### FAQ

**Q: The dashboard shows all zeros.**
A: No Claude Code requests have passed through Headroom yet. Verify `ANTHROPIC_BASE_URL=http://localhost:8787` in `~\.claude\settings.json`, then start a new Claude Code session.

**Q: Container doesn't restart after changing parameters.**
A: Make sure Docker Desktop is running. The WebUI performs `docker stop → rm → run`.

**Q: How do I shut down?**
A: Close the terminal running `python app.py`. The Headroom container stays up.

---

<h2 id="chinese">中文</h2>

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

### 快速启动

#### 1. 检查环境

```bash
# Python 装了没
python --version
# 如果提示找不到 Python 但你装了 Anaconda：
conda activate base
python --version

# Docker 装了没
docker ps
```

如果没有，安装：
- [Python 3.12+](https://www.python.org/downloads/) 或 [Miniconda](https://docs.anaconda.com/miniconda/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

#### 2. 启动 Headroom 容器

```bash
docker run -d --name headroom --restart unless-stopped -p 8787:8787 ghcr.io/chopratejas/headroom:latest
```

> 第一次运行会自动拉取镜像。访问 `http://localhost:8787/health` 应返回 `{"status":"healthy"}`。

#### 3. 克隆并启动 WebUI

```bash
git clone https://github.com/diyu331/HeadroomWebUI.git
cd HeadroomWebUI
```

**方式 A：pip + venv（推荐，轻量）**
```bash
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS / Linux
pip install flask requests
python app.py
```

**方式 B：conda**
```bash
conda create -n headroom-webui python=3.12 -y
conda activate headroom-webui
pip install flask requests
python app.py
```

浏览器打开 `http://localhost:5000`。

> **Windows 用户也可以双击 `start.bat`。**

#### 4. 把 Claude Code 路由到 Headroom

在看板中打开 **配置 → 系统环境配置**，点击 **Headroom 代理** 保存。

Claude Code 的 `~\.claude\settings.json` 会自动更新。新会话的请求就会经过 Headroom 压缩了。

### 功能说明

| 看板卡片 | 展示内容 |
|---------|---------|
| 运行状态 | 容器健康、运行时间、版本号 |
| 压缩统计 | 节省 tokens、压缩率、压缩前后对比 |
| 请求健康 | 成功率、缓存命中、失败数、限流数 |
| 请求概览 | 总请求数、平均延迟、压缩缓存命中率 |

**配置中心：** 系统路由切换、Headroom 全参数表单、配置快照。
**日志：** 实时容器日志，WARN/ERROR 高亮，一键下载。

### 工作原理

```
浏览器 (localhost:5000)  →  Flask 后端 (app.py)
                             ├── 读写 ~\.claude\settings.json
                             ├── Docker CLI 控制容器
                             └── Headroom API 获取统计
```

### Docker 路径自定义

如果 `docker` 不在系统 PATH 中，在 WebUI 配置页填写 docker.exe 完整路径，或设置：

```bash
set DOCKER_PATH=C:\你的路径\docker.exe
```

### 常见问题

**Q: 看板上全是 0？**
A: 还没有 Claude Code 请求经过 Headroom。确认 `~\.claude\settings.json` 中 `ANTHROPIC_BASE_URL` 为 `http://localhost:8787`，新开会话用一次。

**Q: 修改参数后容器没重启？**
A: 检查 Docker Desktop 是否在运行。WebUI 执行 `docker stop → rm → run`。

**Q: 怎么关掉？**
A: 关掉运行 `python app.py` 的终端窗口。Headroom 容器不受影响。

---

*Last updated: 2026-06-05*
