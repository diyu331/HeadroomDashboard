# Headroom Dashboard — 设计文档

## 概述

Headroom 的**完整配置中心 + 监控看板**，通过网页完成所有操作：
- 查看压缩统计、运行状态、实时日志
- 修改 Headroom 代理的一切参数
- 控制容器启停
- 切换 Claude Code 路由
- 全部在浏览器里完成，**再也不用敲命令或改文件**

## 技术选型

| 层 | 技术 |
|---|---|
| 后端 | Python Flask |
| 前端 | 单页 HTML + Tailwind CSS (CDN) + 原生 JS |
| Python 环境 | Conda 虚拟环境 `headroom-dashboard` |
| 容器控制 | `subprocess` 调用 Docker CLI |
| 配置持久化 | 读写 PowerShell profile.ps1 + Docker recreate 流程 |

## 文件结构

```
D:\developer_tools\HeadroomWebUI\
├── app.py                    # Flask 后端（API、Docker 控制、配置读写）
├── templates\
│   └── index.html            # 前端单页（Tailwind 样式）
├── docs\
│   └── 2026-06-05-headroom-dashboard-design.md
└── README.md                 # 启动说明
```

## 页面布局

### 整体结构

```
┌─ 导航栏 ──────────────────────────────────────────────┐
│  🧠 Headroom Dashboard     [状态] [配置] [日志]       │
├────────────────────────────────────────────────────────┤
│                                                        │
│  （Tab 内容区域，根据导航切换）                          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

三大 Tab，每个独立加载数据。

---

### Tab 1：状态看板

```
┌─ 页眉 ─────────────────────────────────────────────┐
│  🧠 Headroom Dashboard    [🔄 刷新] 上次更新: 12s前  │
├──────────┬──────────┬──────────┬────────────────────┤
│  运行状态  │  压缩统计  │  成本节省  │  请求概览          │
│  ● 健康   │  节省12M  │  省$5.20  │  共423次请求       │
│  运行3h12m │  压缩率67%│  总输入767M│  缓存命中 34%      │
│  版本0.23.0│           │          │  平均延迟 210ms    │
├──────────┴──────────┴──────────┴────────────────────┤
│  ▷ 压缩策略分布                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Kompress    ████████████████████▎  42%      │   │
│  │  Cache       ████████████▎         28%      │   │
│  │  AST压缩     ████████▎             18%      │   │
│  │  JSON压缩    █████▎                12%      │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

展示内容：

| 卡片 | 数据来源 | 指标 |
|------|---------|------|
| 运行状态 | health + docker ps | 健康状态、运行时间、版本、pid |
| 压缩统计 | stats | 总节省 token、压缩率%、各策略分布 |
| 成本节省 | stats.cost | 节省 USD、总输入 token、输入成本 |
| 请求概览 | stats.requests | 总请求数、缓存命中数、平均延迟 |

---

### Tab 2：配置中心（核心功能）

分三块：

#### 2a. Headroom 代理参数

从 `headroom proxy --help` 提取的所有可用参数，按分类展示：

| 分类 | 参数 | 说明 |
|------|------|------|
| **运行模式** | `--mode` | token（压缩优先） / cache（缓存优先） |
|  | `--port` | 代理端口（默认 8787） |
|  | `--workers` | 工作进程数 |
| **优化开关** | `--no-optimize` | 是否开启压缩 |
|  | `--no-cache` | 是否开启缓存 |
|  | `--no-rate-limit` | 是否开启限流 |
|  | `--code-aware` | 是否启用 AST 代码压缩 |
|  | `--intercept-tool-results` | 是否拦截 tool result |
|  | `--code-graph` | 是否启用代码图谱智能 |
| **记忆** | `--memory` | 是否启用持久记忆 |
|  | `--memory-storage` | project / user / global |
|  | `--memory-top-k` | 注入上下文记忆条数 |
|  | `--learn` | 是否启用流量学习 |
| **直连** | `--anthropic-api-url` | **自定义 API 地址**（当前为 DeepSeek） |
|  | `--backend` | anthropic / bedrock / openrouter |
|  | `--region` | 云区域（Bedrock/Vertex 用） |
| **预算日志** | `--budget` | 每日预算上限 USD |
|  | `--no-telemetry` | 是否关闭匿名遥测 |
|  | `--log-file` | 日志文件路径 |
|  | `--log-messages` | 是否记录完整消息 |

**交互方式**：表单填写 + 下拉选择 + 开关。修改后点「保存并重启容器」-> 后端用新参数重新 create + start 容器。

#### 2b. 系统环境配置

| 配置项 | 说明 |
|--------|------|
| **Claude Code 路由** | 下拉切换：Headroom 代理 / 直连 DeepSeek / 自定义 |
| **ANTHROPIC_BASE_URL** | 直接编辑文本框 |
| **Docker 安装路径** | 自动检测，可手动修改 |

**交互方式**：下拉选择或文本框编辑。保存后写入 profile.ps1。

#### 2c. 配置快照

- 显示当前容器启动时的完整命令
- 显示当前 profile.ps1 中 HEADROOM 相关配置节

---

### Tab 3：日志

```
┌─ 日志 ───────────────────────────────────────────────┐
│  📋 Headroom 容器日志（最近 100 行）                  │
│  [🔄 刷新] [⬇ 下载日志]                              │
│  ┌──────────────────────────────────────────────┐   │
│  │ 2026-06-05 09:17:46 INFO  HTTP Request...    │   │
│  │ 2026-06-05 09:18:41 INFO  compression: 72%   │   │
│  │ 2026-06-05 09:19:12 WARN  cache miss for...  │   │
│  │ ...                                          │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

---

## API 路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回首页 HTML |
| **监控** | | |
| `/api/stats` | GET | 聚合状态（stats + health + 容器状态） |
| `/api/logs` | GET | 获取容器日志（?lines=100） |
| **容器控制** | | |
| `/api/container/restart` | POST | 重启容器 |
| `/api/container/stop` | POST | 停止容器 |
| `/api/container/start` | POST | 启动容器 |
| **配置读取** | | |
| `/api/config/headroom` | GET | 读取当前容器参数和环境变量 |
| `/api/config/system` | GET | 读取 profile.ps1 中的配置 |
| `/api/config/all` | GET | 读取所有可配置参数及其当前值 |
| **配置写入** | | |
| `/api/config/headroom` | POST | 更新 Headroom 参数并重建容器 |
| `/api/config/system` | POST | 更新 profile.ps1 中的环境变量 |

## 配置持久化策略

### 修改 Headroom 参数（需要重建容器）

1. 用户调整参数表单，点击「保存」
2. 后端：`docker stop headroom && docker rm headroom`
3. 后端：用新参数 `docker run ...` 创建新容器
4. 前端：提示结果并刷新状态

### 修改系统配置（需要写 profile.ps1）

1. 用户选择/输入新值，点击「保存」
2. 后端：解析 profile.ps1，替换/添加对应行
3. 返回提示：**「已更新，新 PowerShell 窗口生效」**或**「立即生效」（当前会话也设）**

## 错误处理

- 容器停止时，状态卡片显示灰色「已停止」，日志显示「容器未运行」
- 配置保存失败时，页面显示具体错误（权限问题、Docker 不可达等）
- 容器重建失败时，保留旧容器不删除
- 各 Tab 独立加载，切换 Tab 不会丢失其他 Tab 的数据

## 安全性

- 仅监听 localhost，不对外暴露
- 所有操作通过 Flask 后端代理，前端不直接调用 Docker/系统 API
- 配置写入前校验格式

## 文件结构补充

```
├── start.bat                   # 🚀 双击一键启动（自动激活环境 + 开浏览器）
```

## 使用方式

### 一键启动（推荐）

双击 `start.bat`，自动：
1. 激活 conda 环境
2. 启动 Flask 服务器
3. 打开浏览器跳转到看板
4. 保持终端运行（关掉终端即停止服务）

### 手动启动

```powershell
conda activate E:\Data\deve_python_tool\anaconda_env\headroom-dashboard
pip install flask requests
cd D:\developer_tools\HeadroomWebUI
python app.py
# 浏览器打开 http://localhost:5000
```

### 也可以添加桌面快捷方式

在 `start.bat` 上右键 -> 发送到 -> 桌面快捷方式，以后双击桌面图标就行。

## 后续可扩展

- 定时自动刷新（可开关）
- 历史趋势图表（日/周/月 token 节省曲线）
- 多容器管理（如果以后跑多个 Headroom 实例）
