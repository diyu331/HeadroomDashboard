# Headroom Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web dashboard + configuration center for Headroom proxy, with status monitoring, full parameter management, container control, and one-click startup.

**Architecture:** Python Flask backend that proxies Headroom API calls and executes Docker CLI via subprocess. Single-page HTML frontend with 3 Tab views (Dashboard / Config / Logs) using Tailwind CSS CDN. Conda virtual environment for isolation.

**Tech Stack:** Python + Flask + Tailwind CSS (CDN) + Docker CLI + conda

---

## File Structure

```
D:\developer_tools\HeadroomWebUI\
├── app.py                    # Flask 后端 — 所有 API 路由 + Docker 控制 + 配置读写
├── templates\
│   └── index.html            # 前端单页 — 3个 Tab + Tailwind 样式
├── start.bat                 # 双击一键启动
├── docs\
│   ├── 2026-06-05-headroom-dashboard-design.md
│   └── superpowers\plans\
│       └── 2026-06-05-headroom-dashboard.md   # ← 本文件
└── README.md                 # 使用说明
```

---

### Task 1: 创建 Conda 环境并安装依赖

**Files:** (环境配置)

- [ ] **Step 1: 创建 conda 虚拟环境**

```powershell
conda create -p "E:\Data\deve_python_tool\anaconda_env\headroom-dashboard" python=3.12 -y
```

- [ ] **Step 2: 安装依赖**

```powershell
conda activate E:\Data\deve_python_tool\anaconda_env\headroom-dashboard
pip install flask requests
```

---

### Task 2: 编写 Flask 后端 `app.py`

**Files:**
- Create: `D:\developer_tools\HeadroomWebUI\app.py`

- [ ] **Step 1: 导入和配置**

```python
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="templates")

DOCKER_PATH = r"D:\developer_tools\DockerDesktop\resources\bin\docker.exe"
PROFILE_PATH = os.path.expanduser(r"~\Documents\WindowsPowerShell\profile.ps1")
HEADROOM_CONTAINER = "headroom"
HEADROOM_API = "http://localhost:8787"

CONFIG_PARAMS = [
    # (key, flag, type, default, category, label, options)
    # 运行模式
    {"key": "mode", "flag": "--mode", "type": "select", "default": "token",
     "category": "mode", "label": "优化模式",
     "options": [{"value": "token", "label": "Token 优先（最大压缩）"},
                 {"value": "cache", "label": "Cache 优先（提高缓存命中）"}]},
    {"key": "port", "flag": "-p", "type": "number", "default": "8787",
     "category": "mode", "label": "监听端口"},
    {"key": "workers", "flag": "--workers", "type": "number", "default": "1",
     "category": "mode", "label": "工作进程数"},
    # 优化开关
    {"key": "no-optimize", "flag": "--no-optimize", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用压缩（透传模式）"},
    {"key": "no-cache", "flag": "--no-cache", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用语义缓存"},
    {"key": "no-rate-limit", "flag": "--no-rate-limit", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用速率限制"},
    {"key": "code-aware", "flag": "--code-aware", "type": "bool", "default": False,
     "category": "optimization", "label": "启用 AST 代码压缩（需 pip install headroom-ai[code]）"},
    {"key": "intercept-tool-results", "flag": "--intercept-tool-results", "type": "bool", "default": False,
     "category": "optimization", "label": "拦截 Tool Results"},
    {"key": "code-graph", "flag": "--code-graph", "type": "bool", "default": False,
     "category": "optimization", "label": "启用代码图谱智能"},
    # 记忆
    {"key": "memory", "flag": "--memory", "type": "bool", "default": False,
     "category": "memory", "label": "启用持久记忆"},
    {"key": "memory-storage", "flag": "--memory-storage", "type": "select", "default": "project",
     "category": "memory", "label": "记忆存储方式",
     "options": [{"value": "project", "label": "Project（按项目隔离）"},
                 {"value": "user", "label": "User（按用户隔离）"},
                 {"value": "global", "label": "Global（全局共享）"}]},
    {"key": "memory-top-k", "flag": "--memory-top-k", "type": "number", "default": "10",
     "category": "memory", "label": "注入记忆条数"},
    {"key": "learn", "flag": "--learn", "type": "bool", "default": False,
     "category": "memory", "label": "启用流量学习（隐含 --memory）"},
    # 直连
    {"key": "anthropic-api-url", "flag": "--anthropic-api-url", "type": "text", "default": "",
     "category": "backend", "label": "自定义 API 地址",
     "placeholder": "https://api.deepseek.com/anthropic"},
    {"key": "backend", "flag": "--backend", "type": "select", "default": "anthropic",
     "category": "backend", "label": "API 后端",
     "options": [{"value": "anthropic", "label": "Anthropic 直连"},
                 {"value": "bedrock", "label": "AWS Bedrock"},
                 {"value": "openrouter", "label": "OpenRouter"}]},
    {"key": "region", "flag": "--region", "type": "text", "default": "us-west-2",
     "category": "backend", "label": "云区域（Bedrock/Vertex）"},
    # 预算日志
    {"key": "budget", "flag": "--budget", "type": "number", "default": "",
     "category": "log", "label": "每日预算上限（USD）"},
    {"key": "no-telemetry", "flag": "--no-telemetry", "type": "bool", "default": False,
     "category": "log", "label": "关闭匿名遥测"},
    {"key": "log-file", "flag": "--log-file", "type": "text", "default": "",
     "category": "log", "label": "日志文件路径"},
    {"key": "log-messages", "flag": "--log-messages", "type": "bool", "default": False,
     "category": "log", "label": "记录完整消息体"},
]

VALID_BOOL_FALSE = {"", "false", "0", "no", "off", None}


def docker_cmd(*args, capture=True):
    """Execute docker CLI command. Returns stdout text or (rc, stdout, stderr)."""
    cmd = [DOCKER_PATH] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=capture, text=True, timeout=30)
        if capture:
            return r.stdout.strip(), r.stderr.strip(), r.returncode
        return "", "", r.returncode
    except FileNotFoundError:
        return "", "docker not found at " + DOCKER_PATH, -1
    except subprocess.TimeoutExpired:
        return "", "command timed out", -1


def get_container_status():
    """Get full container status details."""
    stdout, stderr, rc = docker_cmd("ps", "-a", "--filter", f"name={HEADROOM_CONTAINER}",
                                     "--format", "{{.ID}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}")
    if rc != 0 or not stdout:
        return {"running": False, "status": "not_found", "detail": stderr or "容器不存在"}

    parts = stdout.split("\t")
    running = "Up" in parts[1] if len(parts) > 1 else False
    return {
        "running": running,
        "status": parts[1] if len(parts) > 1 else "unknown",
        "ports": parts[2] if len(parts) > 2 else "",
        "image": parts[3] if len(parts) > 3 else "",
        "container_id": parts[0],
    }


def get_headroom_health():
    """Query Headroom /health endpoint."""
    try:
        r = requests.get(f"{HEADROOM_API}/health", timeout=5)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except requests.RequestException as e:
        return {"error": str(e)}


def get_headroom_stats():
    """Query Headroom /stats endpoint."""
    try:
        r = requests.get(f"{HEADROOM_API}/stats", timeout=5)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except requests.RequestException as e:
        return {"error": str(e)}


def read_profile():
    """Read the PowerShell profile content."""
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        return f"# Error reading profile: {e}"


def write_profile(content):
    """Write content to PowerShell profile."""
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def get_headroom_config_from_inspect():
    """Parse current container's config from docker inspect."""
    stdout, _, rc = docker_cmd("inspect", HEADROOM_CONTAINER,
                                "--format", "{{json .Config}}")
    if rc != 0 or not stdout:
        return {}

    try:
        config = json.loads(stdout)
        env = {e.split("=", 1)[0]: e.split("=", 1)[1] for e in config.get("Env", []) if "=" in e}
        cmd_parts = config.get("Cmd", [])
        return {"env": env, "cmd": cmd_parts, "image": config.get("Image", "")}
    except (json.JSONDecodeError, IndexError):
        return {}


def build_docker_run_args(params):
    """Build docker run command from config form params."""
    args = ["run", "-d", "--name", HEADROOM_CONTAINER,
            "--restart", "unless-stopped",
            "-p", "8787:8787",
            "-v", f"{os.path.expanduser('~')}/.headroom:/root/.headroom"]

    # Env vars
    env_vars = {}
    if params.get("anthropic-api-url"):
        env_vars["ANTHROPIC_TARGET_API_URL"] = params["anthropic-api-url"]

    # Flag-style params
    bool_on = {"memory", "code-aware", "code-graph", "learn", "intercept-tool-results",
               "no-telemetry", "log-messages"}
    bool_off = {"no-optimize", "no-cache", "no-rate-limit"}

    for p in CONFIG_PARAMS:
        key = p["key"]
        if key in params:
            val = params[key]
            if p["type"] == "bool":
                if key in bool_on and str(val).lower() in ("true", "1", "on", "yes"):
                    args.append(p["flag"])
                elif key in bool_off and str(val).lower() in ("true", "1", "on", "yes"):
                    args.append(p["flag"])
            elif p["type"] in ("text", "number", "select"):
                if val is not None and str(val).strip():
                    args.append(p["flag"])
                    args.append(str(val).strip())

    # Env vars as -e flags
    for k, v in env_vars.items():
        args.extend(["-e", f"{k}={v}"])

    args.append(f"ghcr.io/chopratejas/headroom:latest")
    return args


def recreate_container(params):
    """Stop, remove, and recreate the headroom container with new params."""
    # Stop & remove
    docker_cmd("stop", HEADROOM_CONTAINER, capture=False)
    docker_cmd("rm", HEADROOM_CONTAINER, capture=False)

    # Build & run
    run_args = build_docker_run_args(params)
    stdout, stderr, rc = docker_cmd(*run_args)
    if rc != 0:
        return {"success": False, "error": stderr or stdout, "returncode": rc}

    # Wait a few seconds, then check status
    time.sleep(3)
    status = get_container_status()
    return {"success": status["running"], "container": status, "output": stdout}


# ─── Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/stats")
def api_stats():
    container = get_container_status()
    health = get_headroom_health() if container["running"] else {"error": "container not running"}
    stats = get_headroom_stats() if container["running"] else {"error": "container not running"}
    return jsonify({"container": container, "health": health, "stats": stats})


@app.route("/api/logs")
def api_logs():
    lines = request.args.get("lines", "100")
    stdout, stderr, rc = docker_cmd("logs", HEADROOM_CONTAINER, "--tail", lines,
                                     "--timestamps")
    if rc != 0:
        return jsonify({"error": stderr or stdout, "logs": ""})
    return jsonify({"logs": stdout})


@app.route("/api/container/restart", methods=["POST"])
def api_container_restart():
    _, stderr, rc = docker_cmd("restart", HEADROOM_CONTAINER)
    time.sleep(2)
    status = get_container_status()
    return jsonify({"success": rc == 0 and status["running"],
                    "error": stderr if rc != 0 else None,
                    "container": status})


@app.route("/api/container/stop", methods=["POST"])
def api_container_stop():
    _, stderr, rc = docker_cmd("stop", HEADROOM_CONTAINER)
    status = get_container_status()
    return jsonify({"success": rc == 0,
                    "error": stderr if rc != 0 else None,
                    "container": status})


@app.route("/api/container/start", methods=["POST"])
def api_container_start():
    _, stderr, rc = docker_cmd("start", HEADROOM_CONTAINER)
    time.sleep(2)
    status = get_container_status()
    return jsonify({"success": rc == 0 and status["running"],
                    "error": stderr if rc != 0 else None,
                    "container": status})


@app.route("/api/config/list")
def api_config_list():
    """Return the CONFIG_PARAMS schema definition."""
    return jsonify(CONFIG_PARAMS)


@app.route("/api/config/headroom", methods=["GET"])
def api_config_headroom_get():
    inspect = get_headroom_config_from_inspect()
    return jsonify(inspect)


@app.route("/api/config/headroom", methods=["POST"])
def api_config_headroom_post():
    params = request.get_json()
    if not params:
        return jsonify({"success": False, "error": "无参数"}), 400
    result = recreate_container(params)
    return jsonify(result)


@app.route("/api/config/system", methods=["GET"])
def api_config_system_get():
    content = read_profile()
    # Parse current ANTHROPIC_BASE_URL from profile
    anthro_match = re.search(r'\$env:ANTHROPIC_BASE_URL\s*=\s*"([^"]+)"', content)
    current_url = anthro_match.group(1) if anthro_match else ""

    return jsonify({
        "profile_content": content,
        "anthropic_base_url": current_url,
        "docker_path": DOCKER_PATH,
        "last_modified": os.path.getmtime(PROFILE_PATH) if os.path.exists(PROFILE_PATH) else None,
    })


@app.route("/api/config/system", methods=["POST"])
def api_config_system_post():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "无数据"}), 400

    action = data.get("action", "update_url")

    if action == "update_url":
        new_url = data.get("anthropic_base_url", "")
        content = read_profile()

        # Replace existing ANTHROPIC_BASE_URL line or append
        if re.search(r'\$env:ANTHROPIC_BASE_URL\s*=', content):
            content = re.sub(
                r'\$env:ANTHROPIC_BASE_URL\s*=\s*"[^"]*"',
                f'$env:ANTHROPIC_BASE_URL = "{new_url}"',
                content,
            )
        else:
            # Add after the Headroom comment section or at top
            headroom_section = "# Headroom proxy — Claude Code context compression\n"
            if headroom_section in content:
                content = content.replace(
                    headroom_section,
                    headroom_section + f'$env:ANTHROPIC_BASE_URL = "{new_url}"\n',
                )
            else:
                content = f'{headroom_section}$env:ANTHROPIC_BASE_URL = "{new_url}"\n\n{content}'

        write_profile(content)
        return jsonify({"success": True, "message": "已更新，新 PowerShell 窗口生效"})

    elif action == "update_profile":
        new_content = data.get("profile_content", "")
        write_profile(new_content)
        return jsonify({"success": True, "message": "profile.ps1 已更新"})

    return jsonify({"success": False, "error": f"未知操作: {action}"}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
```

---

### Task 3: 编写前端单页 `templates/index.html`

**Files:**
- Create: `D:\developer_tools\HeadroomWebUI\templates\index.html`

这个文件是核心前端，内容较大，包含：
- Tailwind CSS + Font Awesome CDN
- 3个 Tab 切换（看板 / 配置 / 日志）
- Tab 1: 4个状态卡片 + 压缩策略分布条形图
- Tab 2: Headroom 参数表单（按分类）+ 系统配置 + 配置快照
- Tab 3: 日志面板 + 下载按钮
- 所有交互通过 fetch API 调用后端

- [ ] **Step 1: 编写完整的 HTML 文件**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Headroom Dashboard</title>
    <script src="https://cdn.tailwindcss.com">
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        * { font-family: 'Inter', system-ui, sans-serif; }
        .tab-btn.active { border-bottom: 2px solid #6366f1; color: #6366f1; font-weight: 600; }
        .tab-btn { transition: all 0.2s; }
        .card { transition: transform .15s, box-shadow .15s; }
        .card:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,.08); }
        .bar { transition: width .6s ease; }
        .toast { animation: slideIn .3s ease, fadeOut .3s ease 2.7s forwards; }
        @keyframes slideIn { from { transform: translateY(-100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes fadeOut { to { opacity: 0; transform: translateY(-20px); } }
        .log-line:hover { background: #f1f5f9; }
        .spinner { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .config-section { border: 1px solid #e5e7eb; border-radius: .75rem; padding: 1.25rem; margin-bottom: 1rem; }
        .param-row { display: flex; align-items: center; padding: .5rem 0; border-bottom: 1px solid #f3f4f6; }
        .param-row:last-child { border-bottom: none; }
        .param-label { flex: 0 0 200px; font-size: .875rem; color: #374151; }
        .param-input { flex: 1; }
        .param-input input[type="text"], .param-input input[type="number"], .param-input select {
            width: 100%; padding: .375rem .75rem; border: 1px solid #d1d5db; border-radius: .375rem; font-size: .875rem;
        }
        .param-input input:focus, .param-input select:focus { outline: none; border-color: #6366f1; ring: 2px solid #6366f1; }
        .toggle { position: relative; width: 44px; height: 24px; cursor: pointer; }
        .toggle input { display: none; }
        .toggle-slider { position: absolute; inset: 0; background: #d1d5db; border-radius: 12px; transition: .3s; }
        .toggle-slider::before { content: ''; position: absolute; width: 20px; height: 20px; left: 2px; bottom: 2px;
            background: white; border-radius: 50%; transition: .3s; }
        .toggle input:checked + .toggle-slider { background: #6366f1; }
        .toggle input:checked + .toggle-slider::before { transform: translateX(20px); }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">

<!-- Navigation -->
<nav class="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center text-white text-sm font-bold">H</div>
                <span class="text-lg font-semibold text-gray-900">Headroom Dashboard</span>
            </div>
            <div class="flex items-center gap-1" id="tabNav">
                <button class="tab-btn active px-4 py-2 text-sm text-gray-500" data-tab="dashboard">
                    <i class="fas fa-chart-pie mr-1.5"></i>状态
                </button>
                <button class="tab-btn px-4 py-2 text-sm text-gray-500" data-tab="config">
                    <i class="fas fa-cog mr-1.5"></i>配置
                </button>
                <button class="tab-btn px-4 py-2 text-sm text-gray-500" data-tab="logs">
                    <i class="fas fa-list mr-1.5"></i>日志
                </button>
            </div>
        </div>
    </div>
</nav>

<!-- Toast notification -->
<div id="toast" class="fixed top-4 right-4 z-50 hidden"></div>

<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

    <!-- Tab: Dashboard -->
    <div class="tab-content active" id="tab-dashboard">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold text-gray-800"><i class="fas fa-chart-pie text-indigo-500 mr-2"></i>状态看板</h2>
            <div class="flex items-center gap-3">
                <span id="lastUpdate" class="text-xs text-gray-400"></span>
                <button onclick="refreshDashboard()" class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100 transition">
                    <i class="fas fa-sync-alt text-xs"></i>刷新
                </button>
            </div>
        </div>

        <!-- 4 Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6" id="cardsContainer">
            <!-- Card 1: Status -->
            <div class="card bg-white rounded-xl p-5 border border-gray-200" id="cardStatus">
                <div class="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wider mb-3">
                    <i class="fas fa-heartbeat"></i><span>运行状态</span>
                </div>
                <div id="cardStatusContent" class="space-y-1.5 text-sm">
                    <div class="animate-pulse h-4 bg-gray-200 rounded w-3/4"></div>
                    <div class="animate-pulse h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
            </div>
            <!-- Card 2: Compression -->
            <div class="card bg-white rounded-xl p-5 border border-gray-200" id="cardCompression">
                <div class="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wider mb-3">
                    <i class="fas fa-compress-alt"></i><span>压缩统计</span>
                </div>
                <div id="cardCompressionContent" class="space-y-1.5 text-sm">
                    <div class="animate-pulse h-4 bg-gray-200 rounded w-3/4"></div>
                    <div class="animate-pulse h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
            </div>
            <!-- Card 3: Cost -->
            <div class="card bg-white rounded-xl p-5 border border-gray-200" id="cardCost">
                <div class="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wider mb-3">
                    <i class="fas fa-dollar-sign"></i><span>成本节省</span>
                </div>
                <div id="cardCostContent" class="space-y-1.5 text-sm">
                    <div class="animate-pulse h-4 bg-gray-200 rounded w-3/4"></div>
                    <div class="animate-pulse h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
            </div>
            <!-- Card 4: Requests -->
            <div class="card bg-white rounded-xl p-5 border border-gray-200" id="cardRequests">
                <div class="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wider mb-3">
                    <i class="fas fa-exchange-alt"></i><span>请求概览</span>
                </div>
                <div id="cardRequestsContent" class="space-y-1.5 text-sm">
                    <div class="animate-pulse h-4 bg-gray-200 rounded w-3/4"></div>
                    <div class="animate-pulse h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
            </div>
        </div>

        <!-- Container control -->
        <div class="bg-white rounded-xl p-5 border border-gray-200 mb-6">
            <h3 class="text-sm font-medium text-gray-700 mb-3"><i class="fas fa-server text-indigo-400 mr-2"></i>容器控制</h3>
            <div class="flex items-center gap-3" id="controlButtons">
                <button onclick="containerAction('restart')" class="px-4 py-2 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg hover:bg-amber-100 text-sm flex items-center gap-2 transition">
                    <i class="fas fa-redo-alt"></i>重启
                </button>
                <button onclick="containerAction('stop')" class="px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded-lg hover:bg-red-100 text-sm flex items-center gap-2 transition">
                    <i class="fas fa-stop"></i>停止
                </button>
                <button onclick="containerAction('start')" class="px-4 py-2 bg-green-50 text-green-700 border border-green-200 rounded-lg hover:bg-green-100 text-sm flex items-center gap-2 transition">
                    <i class="fas fa-play"></i>启动
                </button>
                <span id="controlResult" class="text-xs text-gray-400"></span>
            </div>
        </div>

        <!-- Strategy breakdown -->
        <div class="bg-white rounded-xl p-5 border border-gray-200">
            <h3 class="text-sm font-medium text-gray-700 mb-3"><i class="fas fa-chart-bar text-indigo-400 mr-2"></i>压缩策略分布</h3>
            <div id="strategyBars" class="space-y-2.5">
                <div class="animate-pulse h-5 bg-gray-200 rounded w-full"></div>
                <div class="animate-pulse h-5 bg-gray-200 rounded w-full"></div>
                <div class="animate-pulse h-5 bg-gray-200 rounded w-full"></div>
            </div>
        </div>
    </div>

    <!-- Tab: Config -->
    <div class="tab-content" id="tab-config">
        <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold text-gray-800"><i class="fas fa-cog text-indigo-500 mr-2"></i>配置中心</h2>
            <div class="flex items-center gap-2">
                <span id="configSaveStatus" class="text-xs text-gray-400"></span>
                <button onclick="loadConfig()" class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition">
                    <i class="fas fa-sync-alt text-xs"></i>刷新
                </button>
            </div>
        </div>

        <!-- System Config -->
        <div class="config-section bg-white">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-base font-medium text-gray-800"><i class="fas fa-globe text-indigo-400 mr-2"></i>系统环境配置</h3>
            </div>
            <div class="space-y-3">
                <div class="param-row">
                    <div class="param-label"><i class="fas fa-route text-gray-400 w-4 mr-1.5"></i>Claude Code 路由</div>
                    <div class="param-input">
                        <select id="sysRouteSelect" onchange="onRouteChange()">
                            <option value="http://localhost:8787">通过 Headroom 代理 (localhost:8787)</option>
                            <option value="https://api.deepseek.com/anthropic">直连 DeepSeek</option>
                            <option value="__custom__">自定义</option>
                        </select>
                    </div>
                </div>
                <div class="param-row">
                    <div class="param-label"><i class="fas fa-link text-gray-400 w-4 mr-1.5"></i>ANTHROPIC_BASE_URL</div>
                    <div class="param-input">
                        <input type="text" id="sysAnthropicUrl" placeholder="https://api.deepseek.com/anthropic" />
                    </div>
                </div>
                <div class="param-row">
                    <div class="param-label"><i class="fas fa-docker text-gray-400 w-4 mr-1.5"></i>Docker 路径</div>
                    <div class="param-input">
                        <input type="text" id="sysDockerPath" class="bg-gray-50 text-gray-500" readonly />
                    </div>
                </div>
                <div class="flex justify-end pt-2">
                    <button onclick="saveSystemConfig()" class="px-4 py-2 bg-indigo-500 text-white text-sm rounded-lg hover:bg-indigo-600 transition flex items-center gap-2">
                        <i class="fas fa-save"></i>保存系统配置
                    </button>
                </div>
            </div>
        </div>

        <!-- Headroom Params -->
        <div class="config-section bg-white">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-base font-medium text-gray-800"><i class="fas fa-sliders-h text-indigo-400 mr-2"></i>Headroom 代理参数</h3>
            </div>
            <div id="headroomParamsContainer">
                <div class="text-center py-8 text-gray-400"><i class="fas fa-spinner spinner mr-2"></i>加载参数...</div>
            </div>
            <div class="flex justify-end pt-3 border-t border-gray-100 mt-3">
                <button onclick="saveHeadroomConfig()" class="px-4 py-2 bg-indigo-500 text-white text-sm rounded-lg hover:bg-indigo-600 transition flex items-center gap-2">
                    <i class="fas fa-redo-alt"></i>保存并重启容器
                </button>
            </div>
        </div>

        <!-- Config Snapshot -->
        <div class="config-section bg-white">
            <div class="flex items-center justify-between mb-3">
                <h3 class="text-base font-medium text-gray-800"><i class="fas fa-camera text-indigo-400 mr-2"></i>配置快照</h3>
                <button onclick="loadSnapshot()" class="text-xs text-indigo-500 hover:text-indigo-700"><i class="fas fa-sync-alt mr-1"></i>刷新</button>
            </div>
            <div id="snapshotContent" class="text-xs text-gray-500">
                <div class="animate-pulse h-12 bg-gray-100 rounded"></div>
            </div>
        </div>
    </div>

    <!-- Tab: Logs -->
    <div class="tab-content" id="tab-logs">
        <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold text-gray-800"><i class="fas fa-list text-indigo-500 mr-2"></i>容器日志</h2>
            <div class="flex items-center gap-2">
                <span id="logLineCount" class="text-xs text-gray-400"></span>
                <button onclick="refreshLogs()" class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition">
                    <i class="fas fa-sync-alt text-xs"></i>刷新
                </button>
                <button onclick="downloadLogs()" class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition">
                    <i class="fas fa-download text-xs"></i>下载
                </button>
            </div>
        </div>
        <div class="bg-gray-900 rounded-xl p-4 border border-gray-700" style="min-height: 400px;">
            <pre id="logContent" class="text-xs text-gray-300 font-mono whitespace-pre-wrap overflow-auto" style="max-height: 600px;">
                <div class="animate-pulse text-gray-500">正在加载日志...</div>
            </pre>
        </div>
    </div>

</main>

<script>
    // ─── Tab Switching ─────────────────────────────────────────────────────
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');

            if (btn.dataset.tab === 'dashboard') refreshDashboard();
            if (btn.dataset.tab === 'config') loadConfig();
            if (btn.dataset.tab === 'logs') refreshLogs();
        });
    });

    // ─── Toast ─────────────────────────────────────────────────────────────
    function showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        const colors = { success: 'bg-green-500', error: 'bg-red-500', info: 'bg-blue-500' };
        toast.className = `fixed top-4 right-4 z-50 toast ${colors[type] || 'bg-gray-700'} text-white px-4 py-2.5 rounded-lg shadow-lg text-sm flex items-center gap-2`;
        const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
        toast.innerHTML = `<i class="fas ${icons[type] || 'fa-info-circle'}"></i> ${message}`;
        toast.classList.remove('hidden');
        setTimeout(() => { toast.classList.add('hidden'); }, 3000);
    }

    // ─── Format Helpers ─────────────────────────────────────────────────────
    function fmtNum(n) {
        if (n == null || isNaN(n)) return '0';
        if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
        if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
        if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
        return Math.round(n).toLocaleString();
    }

    function fmtTime(s) {
        if (!s) return '-';
        const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
        if (h > 0) return `${h}h${m}m`;
        return `${m}m${Math.floor(s % 60)}s`;
    }

    function fmtPct(v) { return (v * 100).toFixed(1) + '%'; }

    function fmtMoney(v) {
        if (v == null || v === 0) return '$0.00';
        return '$' + v.toFixed(2);
    }

    // ─── Dashboard ─────────────────────────────────────────────────────────
    async function refreshDashboard() {
        document.getElementById('lastUpdate').textContent = '正在加载...';
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            renderCards(data);
            renderStrategies(data);
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        } catch (e) {
            document.getElementById('lastUpdate').textContent = '加载失败';
            showToast('加载状态失败: ' + e.message, 'error');
        }
    }

    function renderCards(data) {
        const c = data.container || {};
        const h = data.health || {};
        const s = data.stats || {};

        // Card 1: Status
        const isHealthy = c.running && h.status === 'healthy';
        const uptime = h.uptime_seconds || 0;
        document.getElementById('cardStatusContent').innerHTML = `
            <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full ${isHealthy ? 'bg-green-500' : c.running ? 'bg-yellow-400' : 'bg-red-400'}"></span>
                <span class="font-medium ${isHealthy ? 'text-green-700' : c.running ? 'text-yellow-700' : 'text-red-700'}">
                    ${isHealthy ? '健康' : c.running ? '启动中' : '已停止'}
                </span>
            </div>
            <div class="text-gray-500">运行 ${fmtTime(uptime)}</div>
            <div class="text-gray-400 text-xs">v${h.version || '-'} · ${c.container_id ? c.container_id.slice(0, 12) : '-'}</div>
        `;

        // Card 2: Compression
        const comp = s.summary?.compression || {};
        const allLayersPct = s.tokens?.all_layers_savings_percent != null ? s.tokens.all_layers_savings_percent : 0;
        const allLayersSaved = s.tokens?.all_layers_saved || 0;
        document.getElementById('cardCompressionContent').innerHTML = `
            <div class="text-2xl font-bold text-gray-800">${fmtNum(allLayersSaved)}</div>
            <div class="text-gray-500">总节省 Tokens</div>
            <div class="flex items-center gap-1.5">
                <span class="text-lg font-semibold text-green-600">${allLayersPct.toFixed(1)}%</span>
                <span class="text-gray-400 text-xs">压缩率</span>
            </div>
        `;

        // Card 3: Cost
        const cost = s.cost || {};
        document.getElementById('cardCostContent').innerHTML = `
            <div class="text-2xl font-bold text-green-600">${fmtMoney(cost.savings_usd)}</div>
            <div class="text-gray-500">已节省成本</div>
            <div class="text-gray-500 text-xs">总输入: ${fmtNum(cost.total_input_tokens)} tokens</div>
        `;

        // Card 4: Requests
        const req = s.requests || {};
        const prefix = s.prefix_cache?.totals || {};
        const hitRate = prefix.request_hit_rate != null ? (prefix.request_hit_rate * 100).toFixed(0) : '-';
        document.getElementById('cardRequestsContent').innerHTML = `
            <div class="text-2xl font-bold text-gray-800">${fmtNum(req.total)}</div>
            <div class="text-gray-500">总请求</div>
            <div class="flex items-center gap-3 text-xs text-gray-500">
                <span><i class="fas fa-database mr-1"></i>缓存 ${hitRate}%</span>
                <span><i class="fas fa-clock mr-1"></i>${s.latency?.average_ms ? s.latency.average_ms.toFixed(0) + 'ms' : '-'}</span>
            </div>
        `;
    }

    function renderStrategies(data) {
        const s = data.stats || {};
        const strategies = s.compressions_by_strategy || {};
        const keys = Object.keys(strategies);
        const container = document.getElementById('strategyBars');

        if (!keys.length) {
            container.innerHTML = '<div class="text-sm text-gray-400 py-4 text-center">暂无压缩数据（使用 Headroom 后才会产生）</div>';
            return;
        }

        const total = keys.reduce((sum, k) => sum + (strategies[k] || 0), 0);
        const colors = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#818cf8', '#7c3aed'];
        const labels = { kompress: 'Kompress', ast: 'AST 压缩', json: 'JSON 压缩', cache: '缓存', prefix: '前缀缓存',
                        cli_filtering: 'CLI 过滤', rtk: 'RTK', lean_ctx: 'Lean CTX', default: '其他' };

        container.innerHTML = keys.map((k, i) => {
            const val = strategies[k] || 0;
            const pct = total > 0 ? (val / total * 100) : 0;
            const label = labels[k.toLowerCase()] || k;
            const color = colors[i % colors.length];
            return `
                <div class="flex items-center gap-3">
                    <span class="text-xs text-gray-500 w-20 text-right">${label}</span>
                    <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                        <div class="bar h-full rounded-full" style="width: ${pct}%; background: ${color}"></div>
                    </div>
                    <span class="text-xs font-medium text-gray-600 w-16">${pct.toFixed(1)}%</span>
                    <span class="text-xs text-gray-400 w-20">${fmtNum(val)}</span>
                </div>
            `;
        }).join('');
    }

    // ─── Container Control ────────────────────────────────────────────────
    async function containerAction(action) {
        const labels = { restart: '重启', stop: '停止', start: '启动' };
        const btn = event.target.closest('button');
        const resultEl = document.getElementById('controlResult');
        if (btn) btn.disabled = true;
        resultEl.innerHTML = `<i class="fas fa-spinner spinner mr-1"></i>正在${labels[action]}...`;
        try {
            const res = await fetch(`/api/container/${action}`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showToast(`容器已${labels[action]}`, 'success');
                refreshDashboard();
            } else {
                resultEl.textContent = `${labels[action]}失败: ${data.error || '未知错误'}`;
                showToast(`${labels[action]}失败`, 'error');
            }
        } catch (e) {
            resultEl.textContent = `请求失败: ${e.message}`;
            showToast(`请求失败: ${e.message}`, 'error');
        }
        if (btn) btn.disabled = false;
    }

    // ─── Config ────────────────────────────────────────────────────────────
    let configSchema = [];

    async function loadConfig() {
        await Promise.all([loadSystemConfig(), loadHeadroomParams(), loadSnapshot()]);
    }

    async function loadSystemConfig() {
        try {
            const res = await fetch('/api/config/system');
            const data = await res.json();
            document.getElementById('sysAnthropicUrl').value = data.anthropic_base_url || '';
            document.getElementById('sysDockerPath').value = data.docker_path || '';
            // Set dropdown
            const sel = document.getElementById('sysRouteSelect');
            sel.value = data.anthropic_base_url;
            if (sel.value !== data.anthropic_base_url) sel.value = '__custom__';
        } catch (e) { showToast('加载系统配置失败: ' + e.message, 'error'); }
    }

    function onRouteChange() {
        const sel = document.getElementById('sysRouteSelect');
        const input = document.getElementById('sysAnthropicUrl');
        if (sel.value !== '__custom__') input.value = sel.value;
    }

    async function saveSystemConfig() {
        const url = document.getElementById('sysAnthropicUrl').value.trim();
        if (!url) { showToast('请输入 ANTHROPIC_BASE_URL', 'error'); return; }
        try {
            const res = await fetch('/api/config/system', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'update_url', anthropic_base_url: url }),
            });
            const data = await res.json();
            if (data.success) {
                showToast(data.message, 'success');
            } else {
                showToast('保存失败: ' + (data.error || '未知错误'), 'error');
            }
        } catch (e) { showToast('请求失败: ' + e.message, 'error'); }
    }

    async function loadHeadroomParams() {
        try {
            const res = await fetch('/api/config/list');
            configSchema = await res.json();
            // Also load current values
            const curRes = await fetch('/api/config/headroom');
            const current = await curRes.json();
            renderHeadroomForm(current);
        } catch (e) { showToast('加载参数失败: ' + e.message, 'error'); }
    }

    function renderHeadroomForm(current) {
        const env = current.env || {};
        const cmd = current.cmd || [];
        const container = document.getElementById('headroomParamsContainer');
        const categories = [
            { key: 'mode', label: '运行模式', icon: 'fa-play-circle' },
            { key: 'optimization', label: '优化开关', icon: 'fa-toggle-on' },
            { key: 'memory', label: '记忆', icon: 'fa-brain' },
            { key: 'backend', label: '直连与后端', icon: 'fa-server' },
            { key: 'log', label: '预算与日志', icon: 'fa-chart-line' },
        ];

        let html = '';
        for (const cat of categories) {
            const params = configSchema.filter(p => p.category === cat.key);
            if (!params.length) continue;
            html += `<div class="mb-4"><h4 class="text-sm font-medium text-gray-600 mb-2"><i class="fas ${cat.icon} text-indigo-300 mr-1.5"></i>${cat.label}</h4>`;
            for (const p of params) {
                const id = `hparam-${p.key}`;
                // Determine current value
                let curVal = p.default;
                // Check docker env for ANTHROPIC_TARGET_API_URL
                if (p.key === 'anthropic-api-url' && env.ANTHROPIC_TARGET_API_URL) curVal = env.ANTHROPIC_TARGET_API_URL;
                // Check cmd flags
                const idx = cmd.indexOf(p.flag === '-p' ? '-p' : p.flag);
                if (idx >= 0 && p.type !== 'bool') curVal = cmd[idx + 1] || curVal;
                if (idx >= 0 && p.type === 'bool') curVal = true;

                html += `<div class="param-row">`;
                html += `<div class="param-label">${p.label}</div>`;
                html += `<div class="param-input">`;
                if (p.type === 'bool') {
                    const checked = curVal === true || str(curVal).toLowerCase() === 'true';
                    html += `<label class="toggle"><input type="checkbox" id="${id}" ${checked ? 'checked' : ''}><span class="toggle-slider"></span></label>`;
                } else if (p.type === 'select') {
                    html += `<select id="${id}">`;
                    for (const opt of p.options || []) {
                        html += `<option value="${opt.value}" ${curVal === opt.value ? 'selected' : ''}>${opt.label}</option>`;
                    }
                    html += `</select>`;
                } else if (p.type === 'number') {
                    html += `<input type="number" id="${id}" value="${curVal || ''}" ${p.placeholder ? `placeholder="${p.placeholder}"` : ''} />`;
                } else {
                    html += `<input type="text" id="${id}" value="${curVal || ''}" ${p.placeholder ? `placeholder="${p.placeholder}"` : ''} />`;
                }
                html += `</div></div>`;
            }
            html += `</div>`;
        }
        container.innerHTML = html;
    }

    function str(v) { return String(v || ''); }

    async function saveHeadroomConfig() {
        const params = {};
        for (const p of configSchema) {
            const el = document.getElementById(`hparam-${p.key}`);
            if (!el) continue;
            if (p.type === 'bool') params[p.key] = el.checked;
            else params[p.key] = el.value;
        }

        try {
            const res = await fetch('/api/config/headroom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params),
            });
            const data = await res.json();
            if (data.success) {
                showToast('容器已用新参数重启', 'success');
                setTimeout(loadConfig, 1000);
            } else {
                showToast('失败: ' + (data.error || '未知错误'), 'error');
            }
        } catch (e) { showToast('请求失败: ' + e.message, 'error'); }
    }

    async function loadSnapshot() {
        try {
            const [sysRes, hrRes] = await Promise.all([
                fetch('/api/config/system'),
                fetch('/api/config/headroom'),
            ]);
            const sys = await sysRes.json();
            const hr = await hrRes.json();
            const cmd = (hr.cmd || []).join(' ');
            const env = hr.env || {};
            const profileHeadroomSection = (sys.profile_content || '').split('\\n')
                .filter(l => l.includes('HEADROOM') || l.includes('ANTHROPIC_BASE_URL') || l.includes('headroom')).join('\\n');

            document.getElementById('snapshotContent').innerHTML = `
                <div class="space-y-2">
                    <div><span class="font-medium text-gray-600">容器启动命令:</span>
                        <pre class="mt-1 bg-gray-50 p-2 rounded text-xs overflow-x-auto">docker ${cmd}</pre>
                    </div>
                    <div><span class="font-medium text-gray-600">环境变量:</span>
                        <pre class="mt-1 bg-gray-50 p-2 rounded text-xs overflow-x-auto">${JSON.stringify(env, null, 2)}</pre>
                    </div>
                    <div><span class="font-medium text-gray-600">Profile 配置:</span>
                        <pre class="mt-1 bg-gray-50 p-2 rounded text-xs overflow-x-auto">${profileHeadroomSection || '(未配置)'}</pre>
                    </div>
                </div>
            `;
        } catch (e) {
            document.getElementById('snapshotContent').innerHTML = `<div class="text-sm text-red-400">加载失败: ${e.message}</div>`;
        }
    }

    // ─── Logs ──────────────────────────────────────────────────────────────
    async function refreshLogs() {
        const pre = document.getElementById('logContent');
        pre.innerHTML = '<span class="text-gray-400">正在加载日志...</span>';
        try {
            const res = await fetch('/api/logs?lines=100');
            const data = await res.json();
            if (data.error) {
                pre.innerHTML = `<span class="text-red-400">${data.error}</span>`;
                return;
            }
            const lines = (data.logs || '').split('\\n').filter(Boolean);
            document.getElementById('logLineCount').textContent = lines.length + ' 行';
            pre.innerHTML = lines.map(l => {
                const ts = l.slice(0, 30);
                const rest = l.slice(30);
                let colorClass = 'text-gray-300';
                if (rest.includes('WARN') || rest.includes('warn')) colorClass = 'text-yellow-300';
                if (rest.includes('ERROR') || rest.includes('error') || rest.includes('Error')) colorClass = 'text-red-300';
                if (rest.includes('compression') || rest.includes('saved')) colorClass = 'text-green-300';
                return `<div class="log-line py-0.5 px-1 -mx-1 rounded"><span class="text-gray-500">${ts}</span><span class="${colorClass}">${rest}</span></div>`;
            }).join('');
        } catch (e) {
            pre.innerHTML = `<span class="text-red-400">请求失败: ${e.message}</span>`;
        }
    }

    async function downloadLogs() {
        try {
            const res = await fetch('/api/logs?lines=500');
            const data = await res.json();
            const blob = new Blob([data.logs || ''], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `headroom-logs-${new Date().toISOString().slice(0, 19)}.txt`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) { showToast('下载失败: ' + e.message, 'error'); }
    }

    // ─── Init ──────────────────────────────────────────────────────────────
    refreshDashboard();
</script>
</body>
</html>
```

- [ ] **Step 2: 验证文件写入**

确认文件写入成功。

---

### Task 4: 编写一键启动脚本 `start.bat`

**Files:**
- Create: `D:\developer_tools\HeadroomWebUI\start.bat`

- [ ] **Step 1: 创建 start.bat**

```bat
@echo off
title Headroom Dashboard

echo ============================================
echo    Headroom Dashboard - 启动中...
echo ============================================

:: 激活 conda 环境
call conda activate E:\Data\deve_python_tool\anaconda_env\headroom-dashboard
if %errorlevel% neq 0 (
    echo [错误] conda 环境激活失败
    pause
    exit /b 1
)

:: 启动 Flask 应用
echo [INFO] 启动 Web 服务...
start "" http://localhost:5000
python app.py

:: 如果进程退出
echo [INFO] 服务已停止
pause
```

---

### Task 5: 编写启动说明 `README.md`

**Files:**
- Create: `D:\developer_tools\HeadroomWebUI\README.md`

- [ ] **Step 1: 创建 README.md**

```markdown
# Headroom Dashboard

Headroom 代理的本地 Web 配置中心与监控看板。

## 功能

- **状态看板** — 运行状态、压缩统计、成本节省、请求概览
- **配置中心** — Headroom 全部参数在线配置、系统环境配置、配置快照
- **容器控制** — 重启/停止/启动 Headroom 容器
- **日志查看** — 实时查看容器日志，支持下载

## 一键启动

双击 `start.bat`，浏览器自动打开 `http://localhost:5000`

## 手动启动

```powershell
conda activate E:\Data\deve_python_tool\anaconda_env\headroom-dashboard
pip install flask requests
cd D:\developer_tools\HeadroomWebUI
python app.py
```

浏览器打开 `http://localhost:5000`

## 技术栈

- Python 3.12 + Flask
- Tailwind CSS (CDN) + 原生 JavaScript
- Docker CLI
- Conda 虚拟环境

## 目录结构

```
├── app.py              # Flask 后端
├── templates/
│   └── index.html      # 前端页面
├── start.bat           # 一键启动脚本
├── docs/               # 设计文档
└── README.md           # 本文件
```
```

---

### Task 6: 创建 Conda 环境并首次运行

- [ ] **Step 1: 创建 conda 环境**

```powershell
conda create -p "E:\Data\deve_python_tool\anaconda_env\headroom-dashboard" python=3.12 -y
```

- [ ] **Step 2: 安装依赖**

```powershell
conda activate E:\Data\deve_python_tool\anaconda_env\headroom-dashboard
pip install flask requests
```

- [ ] **Step 3: 首次启动测试**

```powershell
cd D:\developer_tools\HeadroomWebUI
python app.py
```

浏览器打开 `http://localhost:5000`，验证三个 Tab 均能正常显示数据。
然后 Ctrl+C 停止。
