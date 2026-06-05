# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Headroom Dashboard — 本地 Web 配置中心与监控看板，用于管理 [Headroom](https://github.com/chopratejas/headroom) 代理（Claude Code 上下文压缩代理）。

- **后端**: Python 3.12 + Flask（单文件 `app.py`）
- **前端**: 单页 HTML + Tailwind CSS (CDN) + 原生 JavaScript
- **容器控制**: Docker CLI 子进程调用
- **系统配置**: 读写 PowerShell `profile.ps1`（ANTHROPIC_BASE_URL 环境变量）

## Project Structure

```
├── app.py              # Flask 后端：API 路由、Docker 控制、配置读写
├── templates/
│   └── index.html      # 前端单页：3 个 Tab（状态/配置/日志）
├── start.bat           # 一键启动（激活 conda 环境 → 打开浏览器 → 启动 Flask）
├── docs/               # 设计文档
└── README.md           # 启动说明
```

## Development

### 启动方式

```powershell
# 一键启动（双击 start.bat 或在终端运行）
start.bat

# 手动启动
conda activate E:\Data\deve_python_tool\anaconda_env\headroom-dashboard
pip install flask requests
python app.py
# 浏览器打开 http://localhost:5000
```

### 核心依赖

- `flask` — Web 框架
- `requests` — 调用 Headroom API（`/health`, `/stats`）
- `Docker CLI` — 容器管理（路径硬编码：`D:\developer_tools\DockerDesktop\resources\bin\docker.exe`）
- Conda 环境路径：`E:\Data\deve_python_tool\anaconda_env\headroom-dashboard`

## Architecture

### Flask 后端 (`app.py`)

| 模块 | 功能 |
|------|------|
| `docker_cmd()` | Docker CLI 子进程封装 |
| `get_container_status()` | 读取容器运行状态 |
| `get_headroom_health()`, `get_headroom_stats()` | 调用 Headroom 内部 API |
| `read_profile()`, `write_profile()` | 读写 PowerShell profile.ps1 |
| `build_docker_run_args()` | 从前端参数构建 `docker run` 命令 |
| `recreate_container()` | 停止 → 删除 → 用新参数重建容器 |
| `CONFIG_PARAMS` | Headroom 所有可配置参数的定义（含 type/category/label/options） |

### API 路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回首页 HTML |
| `/api/stats` | GET | 聚合状态（容器 + health + stats 指标） |
| `/api/logs` | GET | 容器日志（`?lines=100`） |
| `/api/container/restart\|stop\|start` | POST | 容器生命周期控制 |
| `/api/config/list` | GET | 返回 `CONFIG_PARAMS` 参数定义列表 |
| `/api/config/headroom` | GET/POST | 读取/更新 Headroom 容器参数（POST 会重建容器） |
| `/api/config/system` | GET/POST | 读取/更新 profile.ps1 系统配置 |

### 配置持久化机制

1. **Headroom 参数修改** → POST `/api/config/headroom` → `recreate_container()` → `docker stop && docker rm && docker run`（重建容器）
2. **系统配置修改** → POST `/api/config/system` → 正则解析/替换 profile.ps1 中的 `$env:ANTHROPIC_BASE_URL` → 新 PowerShell 窗口生效
3. **配置快照** → 读取当前容器 inspect 信息 + profile.ps1，在前端展示

### 前端架构 (`index.html`)

- 3 个 Tab：Dashboard（状态看板 + 容器控制 + 策略分布）、Config（系统配置 + Headroom 参数 + 快照）、Logs
- 所有 API 请求用 `fetch()` + async/await，无前端框架
- Tailwind CSS CDN + Font Awesome 图标
- 表单控件：toggleswitch（bool 参数）、select（枚举参数）、text/number input
- 错误处理：Toast 通知、加载态骨架屏、按钮 disabled 防重复提交

### 关键设计决策

- **纯单文件后端** — 所有逻辑在 `app.py` 中，无 `__init__.py` 或模块拆分。扩展现有功能时保持此模式
- **容器重建式配置** — Headroom 参数修改后重建容器（stop + rm + run），而非 exec 进去修改。`build_docker_run_args()` 确保参数完整性
- **profile.ps1 即系统配置存储** — 不引入额外配置文件，用正则原地替换 `$env:ANTHROPIC_BASE_URL`
- **Docker 路径硬编码** — 在 `app.py` 顶部常量 `DOCKER_PATH`，未从环境变量解析
- **仅监听 localhost** — `app.run(host="127.0.0.1", port=5000, debug=False)`，不对外暴露
