# HeadroomWebUI

Headroom 代理的本地 Web 配置中心与监控看板。

[Headroom](https://github.com/chopratejas/headroom) 是一个 Claude Code 上下文压缩代理，位于 Claude Code 与 API 后端之间，通过智能压缩减少 token 消耗、降低延迟和成本。

**这个 Dashboard 解决什么问题：**
- Headroom 只有 CLI 参数，没有图形界面，每次改配置要敲一长串 `docker run` 命令
- 看不到实时的压缩统计、缓存命中率、压缩策略分布
- 切换 Claude Code 的路由（代理/直连）需要手动改环境变量

**Dashboard 一站式搞定：**
- 📊 实时监控看板 — 压缩率、节省 tokens、请求健康、延迟
- ⚙️ 可视化参数配置 — 通过表单配置 Headroom，一键保存重启容器
- 🔀 路由切换 — 在「Headroom 代理」和「直连 DeepSeek」之间一键切换
- 📋 容器日志查看 — 无需敲 `docker logs`

## 快速启动

### 环境要求

- **Python 3.12+** — [python.org](https://www.python.org/downloads/)
- **Docker Desktop** — Headroom 容器运行在 Docker 中
- **Docker CLI** 可在命令行中直接调用（`docker ps` 能正常执行）

### 克隆并启动

```bash
# 1. 克隆仓库
git clone https://github.com/diyu331/HeadroomWebUI.git
cd HeadroomWebUI

# 2. 创建虚拟环境（可选但推荐）
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# 3. 安装依赖
pip install flask requests

# 4. 启动
python app.py
```

浏览器打开 `http://localhost:5000`。

### 方式二：双击启动

确保 `docker` 命令和 `python` 命令在系统 PATH 中，然后双击 `start.bat`。

## 功能详情

### 状态看板

| 卡片 | 说明 |
|------|------|
| 运行状态 | 容器健康状态、运行时间、版本号 |
| 压缩统计 | 总节省 Tokens、压缩率、压缩前后对比 |
| 请求健康 | 成功率、缓存数、失败数、限流数 |
| 请求概览 | 总请求数、压缩缓存命中率、平均延迟 |

页面底部显示压缩策略分布（Kompress / 文本 / 搜索 / 智能粉碎 等）和按模型拆分的压缩明细。

### 配置中心

**系统环境配置**
- 一键切换 Claude Code 路由：Headroom 代理 ↔ 直连 DeepSeek ↔ 自定义
- 自动写入 `~/.claude/settings.json`，立即生效
- 同时写入系统环境变量和 `profile.ps1`（兼容 PowerShell）

**Headroom 代理参数**
按分类展示所有可配置参数：
- 运行模式（token 优先 / cache 优先）
- 优化开关（压缩、缓存、限流、AST 压缩、代码图谱等）
- 记忆（持久记忆、存储方式、记忆条数）
- 直连与后端（自定义 API 地址、后端选择、云区域）
- 预算与日志

修改参数后一键保存并自动重建容器（`docker stop → rm → run`）。

**配置快照**
显示当前容器启动命令、环境变量、profile.ps1 配置节。

### 日志

查看 Headroom 容器最近日志，支持按级别高亮（WARN/ERROR）、一键下载。

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│              浏览器 (http://localhost:5000)           │
├─────────────────────────────────────────────────────┤
│               Flask 后端 (app.py)                     │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ 监控 API  │  │ 配置管理 API  │  │ 容器控制 API    │  │
│  └────┬─────┘  └──────┬──────┘  └───────┬────────┘  │
├───────┼───────────────┼──────────────────┼───────────┤
│       │               │                  │            │
│  Headroom API     settings.json /     Docker CLI      │
│  /health /stats   profile.ps1 /      docker stop/rm  │
│                   系统环境变量        /restart/start  │
└──────────────────────────────────────────────────────┘
```

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 + Flask |
| 前端 | 单页 HTML + Tailwind CSS (CDN) + 原生 JavaScript |
| 容器控制 | Docker CLI 子进程调用 |
| 配置持久化 | settings.json / profile.ps1 / 系统环境变量 |

## Docker 路径配置

Dashboard 默认调用系统 `docker` 命令。如果你的 Docker CLI 不在 PATH 中，可以设置环境变量：

```bash
set DOCKER_PATH=C:\Program Files\Docker\Docker\resources\bin\docker.exe
```

或者在系统配置页面填写。

## 修改记录

- 2026-06-05: 初始版本
