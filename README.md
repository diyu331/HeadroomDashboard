# Headroom Dashboard

[**English**](#english) · [**中文**](#chinese)

---

<h2 id="english">English</h2>

Local web dashboard for managing the [Headroom](https://github.com/chopratejas/headroom) proxy — a context compression layer for Claude Code that sits between the client and your API backend, reducing token consumption, latency, and cost.

**Features:**
- 📊 **Dashboard** — compression ratio, tokens saved, request health, latency at a glance
- ⚙️ **Visual config** — edit Headroom parameters through a form, save and auto-rebuild the container
- 🔀 **One-click routing** — toggle Claude Code between "via Headroom proxy" and "direct to API backend"
- 📋 **Built-in log viewer** — syntax-highlighted, one-click download
- 🚀 **Splash screen** — real-time startup progress with phase indicators and progress bar

---

### Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Any | `docker ps` |
| [Python](https://www.python.org/downloads/) | 3.12+ | `python --version` |
| [Node.js](https://nodejs.org/) (for frontend build) | 18+ | `node --version` |

> **Note:** Docker Desktop must be **running** before starting the dashboard.

---

### Quick Start

#### Step 1: Start the Headroom container

> Choose the tab for your platform:

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
docker run -d --name headroom --restart unless-stopped -p 8787:8787 `
  -v "$env:USERPROFILE\.headroom:/root/.headroom" `
  -e HF_ENDPOINT=https://hf-mirror.com `
  ghcr.io/chopratejas/headroom:latest `
  --mode token --port 8787 --workers 1 `
  --code-aware --code-graph `
  --anthropic-api-url https://api.deepseek.com/anthropic `
  --backend anthropic
```

</details>

<details>
<summary><b>macOS / Linux</b></summary>

```bash
docker run -d --name headroom --restart unless-stopped -p 8787:8787 \
  -v "$HOME/.headroom:/root/.headroom" \
  -e HF_ENDPOINT=https://hf-mirror.com \
  ghcr.io/chopratejas/headroom:latest \
  --mode token --port 8787 --workers 1 \
  --code-aware --code-graph \
  --anthropic-api-url https://api.deepseek.com/anthropic \
  --backend anthropic
```

</details>

Verify it's running:
```bash
curl http://localhost:8787/health
# Expected: {"status":"healthy"}
```

> **Network note:** `-e HF_ENDPOINT=https://hf-mirror.com` uses a HuggingFace mirror to avoid download failures in regions where `huggingface.co` is inaccessible.

#### Step 2: Clone and start the WebUI

```bash
git clone https://github.com/diyu331/HeadroomDashboard.git
cd HeadroomDashboard
```

**All platforms:**

```bash
# 1. Build the Vue 3 frontend
cd frontend
npm install
npm run build
cd ..

# 2. Install Python dependencies
pip install flask requests

# 3. Start the server
python app.py
```

> **💡 Tip for Python:** It's recommended to use a virtual environment or Conda (e.g. `conda create -n headroom-dashboard python=3.12 && conda activate headroom-dashboard`) before `pip install` to avoid conflicts with system Python packages.

Open `http://localhost:5000` in your browser.

#### Step 3: Route Claude Code through Headroom

Open the WebUI → **Config** tab → click **Headroom proxy** button. This updates `~\.claude\settings.json` automatically. Start a new Claude Code session — all requests will now flow through Headroom.

If you prefer the command line:
```bash
# Set environment variable for current terminal
set ANTHROPIC_BASE_URL=http://localhost:8787
claude
```

---

### Architecture

```
Browser (localhost:5000)
      │
      ├── Vue 3 SPA (frontend/)
      │     └── SplashScreen → MainLayout → Dashboard / Config / Logs
      │
      ▼
Flask backend (app.py)
      │
      ├── reads/writes ~\.claude\settings.json  (routing config)
      ├── reads/writes PowerShell profile.ps1   (system env vars)
      ├── calls Docker CLI                       (container lifecycle)
      └── fetches stats from Headroom API        (localhost:8787)
```

| Layer | Tech | Role |
|-------|------|------|
| Frontend | Vue 3 + Vite + Tailwind CSS | SPA with 4 views, hash-based routing |
| Backend | Python Flask | REST API, Docker control, config persistence |
| Runtime | Python + Flask | Local server, no distribution packaging |
| Container | Docker | Headroom proxy (ghcr.io/chopratejas/headroom) |

---

### Project Structure

```
headroom-dashboard/
├── app.py                 # Flask backend — all API routes and Docker control
├── frontend/              # Vue 3 + Vite source code
│   ├── src/
│   │   ├── views/         # SplashScreen, Dashboard, Config, Logs
│   │   ├── components/    # StatusCard, reusable UI
│   │   └── composables/   # useApi, useStartup, usePolling
│   ├── vite.config.js     # Dev proxy → Flask:5000, build → ../static/
│   └── package.json
├── static/                # Vue build output (served by Flask in production)
├── templates/             # Legacy HTML templates (deprecated)
├── docs/
    └── superpowers/       # Design docs and implementation plans
```

---

### Commands Reference

#### Headroom Container

```bash
# Check status
docker ps --filter name=headroom

# View logs
docker logs headroom

# Stop / Start / Restart
docker stop headroom
docker start headroom
docker restart headroom

# Rebuild with minimum config
docker run -d --name headroom --restart unless-stopped -p 8787:8787 \
  -v "%USERPROFILE%\.headroom:/root/.headroom" \
  -e HF_ENDPOINT=https://hf-mirror.com \
  ghcr.io/chopratejas/headroom:latest \
  --mode token --port 8787 --workers 1 \
  --code-aware --code-graph \
  --anthropic-api-url https://api.deepseek.com/anthropic \
  --backend anthropic
```

#### Frontend

```bash
cd frontend

# Development mode (hot reload)
npm run dev          # → http://localhost:5173 (proxies /api to Flask:5000)

# Production build
npm run build        # outputs to ../static/

# Preview production build
npm run preview
```

#### Flask Backend

```bash
# Start the server
python app.py        # → http://localhost:5000

# Dependencies only
pip install flask requests
```

#### Full Testing

```bash
# Start Flask (terminal 1)
cd HeadroomDashboard
python app.py

# Test all API endpoints (terminal 2)
curl http://localhost:5000/api/startup/status    # Startup phase
curl http://localhost:5000/api/stats             # Dashboard data
curl http://localhost:5000/api/config/list       # Config schema
curl http://localhost:5000/api/config/headroom   # Current container config
curl http://localhost:5000/api/config/system     # System env config
curl http://localhost:5000/api/logs?lines=10     # Container logs
```

---

### API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Vue SPA (production) |
| `/api/stats` | GET | Aggregated dashboard data (container + health + stats) |
| `/api/startup/status` | GET | Startup phase for Splash screen polling |
| `/api/logs?lines=N` | GET | Container logs (default 100 lines) |
| `/api/config/list` | GET | Headroom parameter definitions (schema) |
| `/api/config/headroom` | GET/POST | Read/update Headroom container parameters |
| `/api/config/system` | GET/POST | Read/update system env config (profile.ps1, settings.json) |
| `/api/container/restart\|stop\|start` | POST | Container lifecycle control |

---

### FAQ

**Q: The dashboard shows all zeros.**
A: No Claude Code requests have passed through Headroom yet. Verify `ANTHROPIC_BASE_URL=http://localhost:8787` in `~\.claude\settings.json`, then start a new Claude Code session.

**Q: Container doesn't restart after changing parameters.**
A: Make sure Docker Desktop is running. The WebUI performs `docker stop → rm → run`.

**Q: How do I shut down?**
A: Close the terminal running `python app.py` or press `Ctrl+C`. The Headroom container stays running.

**Q: The Splash screen shows "Docker Desktop 未运行".**
A: Start Docker Desktop manually and click the **Retry** button on the Splash screen.

**Q: First request to Claude Code is still slow after restart.**
A: Headroom's LiteLLM layer lazy-loads on the first `/v1/messages` request (~60s). The dashboard automatically pre-warms it in the background. Wait for the Splash screen to show "Headroom 已就绪" before starting Claude Code.

---

<h2 id="chinese">中文</h2>

Headroom 代理的本地 Web 配置中心与监控看板。使用 Vue 3 前端，实时显示启动进度。

**功能：**
- 📊 **实时看板** — 压缩率、节省 tokens、请求健康、延迟一目了然
- ⚙️ **可视化配置** — 表单填写参数，一键保存并自动重启容器
- 🔀 **一键切换路由** — 「Headroom 代理」↔「直连 DeepSeek」
- 📋 **在线日志** — 自带高亮和下载
- 🚀 **启动进度屏** — 实时显示 Docker 检查、容器启动、Headroom 就绪等阶段

---

### 环境要求

| 软件 | 版本 | 检查命令 |
|------|------|---------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 任意版本 | `docker ps` |
| [Python](https://www.python.org/downloads/) | 3.12+ | `python --version` |
| [Node.js](https://nodejs.org/)（构建前端） | 18+ | `node --version` |

> ⚠️ 启动 Dashboard 之前请确保 Docker Desktop 已运行。

---

### 快速启动

#### 第 1 步：启动 Headroom 容器

```powershell
docker run -d --name headroom --restart unless-stopped -p 8787:8787 ^
  -v "%USERPROFILE%\.headroom:/root/.headroom" ^
  -e HF_ENDPOINT=https://hf-mirror.com ^
  ghcr.io/chopratejas/headroom:latest ^
  --mode token --port 8787 --workers 1 ^
  --code-aware --code-graph ^
  --anthropic-api-url https://api.deepseek.com/anthropic ^
  --backend anthropic
```

验证是否运行成功：
```bash
curl http://localhost:8787/health
# 期望结果: {"status":"healthy"}
```

> 注意 `-e HF_ENDPOINT=https://hf-mirror.com` 使用国内 HuggingFace 镜像，避免模型下载失败。

#### 第 2 步：克隆并启动 WebUI

```bash
git clone https://github.com/diyu331/HeadroomDashboard.git
cd HeadroomDashboard
```

**手动启动（所有平台）**

```bash
# 1. 构建 Vue 3 前端
cd frontend
npm install
npm run build
cd ..

# 2. 安装 Python 依赖
pip install flask requests

# 3. 启动服务器
python app.py
```

浏览器打开 `http://localhost:5000`。

#### 第 3 步：将 Claude Code 路由到 Headroom

打开 WebUI → **配置** Tab → 点击 **Headroom 代理** 按钮。这会自动更新 `~\.claude\settings.json`。新开一个 Claude Code 会话——所有请求就会经过 Headroom 压缩了。

或者命令行方式：
```bash
set ANTHROPIC_BASE_URL=http://localhost:8787
claude
```

---

### 项目结构

```
headroom-dashboard/
├── app.py                 # Flask 后端 — API 路由、Docker 控制、配置读写
├── frontend/              # Vue 3 + Vite 源码
│   ├── src/
│   │   ├── views/         # SplashScreen、Dashboard、Config、Logs
│   │   ├── components/    # StatusCard 等可复用组件
│   │   └── composables/   # useApi、useStartup、usePolling
│   ├── vite.config.js     # 开发代理 → Flask:5000，构建输出 → ../static/
│   └── package.json
├── static/                # Vue 构建产物（生产模式由 Flask 提供）
├── templates/             # 旧的 HTML 模板（已废弃）
├── docs/
    └── superpowers/       # 设计文档和实现计划
```

---

### 命令速查

#### Headroom 容器

```powershell
# 查看状态
docker ps --filter name=headroom

# 查看日志
docker logs headroom

# 停止 / 启动 / 重启
docker stop headroom
docker start headroom
docker restart headroom

# 用最小配置重建
docker run -d --name headroom --restart unless-stopped -p 8787:8787 ^
  -v "%USERPROFILE%\.headroom:/root/.headroom" ^
  -e HF_ENDPOINT=https://hf-mirror.com ^
  ghcr.io/chopratejas/headroom:latest ^
  --mode token --port 8787 --workers 1 ^
  --code-aware --code-graph ^
  --anthropic-api-url https://api.deepseek.com/anthropic ^
  --backend anthropic
```

#### 前端

```bash
cd frontend

# 开发模式（热更新）
npm run dev          # → http://localhost:5173（API 代理到 Flask:5000）

# 生产构建
npm run build        # 输出到 ../static/

# 预览生产构建
npm run preview
```

#### Flask 后端

```bash
# 启动服务器
python app.py        # → http://localhost:5000

# 安装依赖
pip install flask requests
```

---

### API 接口

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/stats` | GET | 聚合看板数据（容器 + 健康 + 统计） |
| `/api/startup/status` | GET | 启动阶段状态（Splash 屏轮询） |
| `/api/logs?lines=N` | GET | 容器日志（默认 100 行） |
| `/api/config/list` | GET | Headroom 参数定义（表单 schema） |
| `/api/config/headroom` | GET/POST | 读取/更新 Headroom 容器参数 |
| `/api/config/system` | GET/POST | 读取/更新系统环境配置 |
| `/api/container/restart\|stop\|start` | POST | 容器生命周期控制 |

---

### 常见问题

**Q: 看板上全是 0？**
A: 还没有 Claude Code 请求经过 Headroom。确认 `~\.claude\settings.json` 中 `ANTHROPIC_BASE_URL` 为 `http://localhost:8787`，新开会话试一次。

**Q: 修改参数后容器没重启？**
A: 检查 Docker Desktop 是否在运行。WebUI 执行 `docker stop → rm → run`。

**Q: 怎么关掉？**
A: `Ctrl+C` 关闭运行 `python app.py` 的终端。Headroom 容器不受影响。

**Q: Splash 屏幕显示 "Docker Desktop 未运行"。**
A: 手动启动 Docker Desktop，然后点击 Splash 屏幕上的**重试**按钮。

**Q: 重启后 Claude Code 第一次请求仍然很慢？**
A: Headroom 的 LiteLLM 层在第一次 `/v1/messages` 请求时才加载（~60s）。Dashboard 会自动在后台预热，等 Splash 页面显示 "Headroom 已就绪" 后再启动 Claude Code 即可。

---

*Last updated: 2026-06-07*
