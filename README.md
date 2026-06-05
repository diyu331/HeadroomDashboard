# Headroom Dashboard

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

- Python 3.12+
- Docker Desktop（Headroom 容器运行在 Docker 中）
- [Headroom](https://github.com/chopratejas/headroom) 镜像（首次启动时自动拉取）

### 方式一：双击启动（推荐）

确保 `start.bat` 中的 conda 环境路径与实际一致，然后双击 `start.bat`。

### 方式二：命令行启动

```bash
# 激活 conda 环境
conda activate E:\Data\deve_python_tool\anaconda_env\headroom-dashboard

# 安装依赖（首次）
pip install flask requests

# 启动
python app.py
```

浏览器打开 `http://localhost:5000`。

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
- 显示配置写入位置：settings.json / 系统环境变量 / profile.ps1

**Headroom 代理参数**
按分类展示所有可配置参数：
- 运行模式（token 优先 / cache 优先）
- 优化开关（压缩、缓存、限流、AST 压缩、代码图谱等）
- 记忆（持久记忆、存储方式、记忆条数）
- 直连与后端（自定义 API 地址、后端选择、云区域）
- 预算与日志

修改参数后一键保存并自动重建容器。

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
│  Headroom API     profile.ps1 /      Docker CLI      │
│  /health /stats   settings.json     docker stop/rm   │
│                                      /restart/start  │
└──────────────────────────────────────────────────────┘
```

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 + Flask |
| 前端 | 单页 HTML + Tailwind CSS (CDN) + 原生 JavaScript |
| 容器控制 | Docker CLI 子进程调用 |
| 配置持久化 | settings.json + profile.ps1 + 系统环境变量 |
| 计费定价 | DeepSeek V4 Flash / Pro（仅参考，实际以 DeepSeek 账单为准） |

## 修改记录

- 2026-06-05: 初始版本
