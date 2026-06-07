import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")

DOCKER_PATH = os.environ.get("DOCKER_PATH", "docker")
PROFILE_PATH = os.path.expanduser(r"~\Documents\WindowsPowerShell\profile.ps1")
CLAUDE_SETTINGS_PATH = os.path.expanduser(r"~\.claude\settings.json")

# ─── DeepSeek V4 Pricing (2026年6月, 人民币计价) ─────────────────────────
# 定价来源：https://api-docs.deepseek.com/zh-cn/quick_start/pricing
# 扣减费用 = token 消耗量 × 模型单价（按缓存未命中标准价计算）
DEEPSEEK_PRICING = {
    "DeepSeek-V4-flash": {
        "name_cn": "DeepSeek V4 Flash",
        "input_cny_per_m": 1.0,        # ¥1/百万 tokens（缓存未命中）
        "input_cache_cny_per_m": 0.02, # ¥0.02/百万（缓存命中）
        "output_cny_per_m": 2.0,       # ¥2/百万 tokens 输出
    },
    "DeepSeek-V4-pro": {
        "name_cn": "DeepSeek V4 Pro",
        "input_cny_per_m": 3.0,
        "input_cache_cny_per_m": 0.025,
        "output_cny_per_m": 6.0,
    },
}
DEFAULT_PRICING = {"name_cn": "DeepSeek V4 Pro", "input_cny_per_m": 3.0, "output_cny_per_m": 6.0}


def get_model_pricing(model_name):
    """查找模型的 DeepSeek 定价，未知模型返回 Flash 价格"""
    for key, pricing in DEEPSEEK_PRICING.items():
        if key.lower() in model_name.lower():
            return pricing
    return DEFAULT_PRICING


def compute_costs(stats):
    """计算各模型压缩概览（仅保留准确数据：tokens、压缩率，不估算费用）"""
    result = {"per_model": {}, "total": {}}
    if not isinstance(stats, dict):
        return result

    cost_data = stats.get("cost")
    if not isinstance(cost_data, dict):
        return result

    per_model = cost_data.get("per_model")
    if not isinstance(per_model, dict) or not per_model:
        return result

    total_output = 0
    tokens_data = stats.get("tokens")
    if isinstance(tokens_data, dict):
        total_output = tokens_data.get("output", 0) or 0

    models_found = {}
    if per_model:
        total_sent = sum(d.get("tokens_sent", 0) for d in per_model.values() if isinstance(d, dict))
        for model_name, model_data in per_model.items():
            if not isinstance(model_data, dict):
                continue
            pricing = get_model_pricing(model_name)
            input_tokens = model_data.get("tokens_sent", 0)
            tokens_saved = model_data.get("tokens_saved", 0)
            original_input = input_tokens + tokens_saved
            requests = model_data.get("requests", 0)

            output_ratio = (input_tokens / total_sent) if total_sent > 0 else 0
            output_tokens = round(total_output * output_ratio)

            models_found[model_name] = {
                "name_cn": pricing["name_cn"],
                "requests": requests,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tokens_saved": tokens_saved,
                "total_before_compression": original_input,
                "savings_percent": model_data.get("reduction_pct", 0),
            }

    result["per_model"] = models_found
    return result

HEADROOM_CONTAINER = "headroom"
HEADROOM_API = "http://localhost:8787"

CONFIG_PARAMS = [
    {"key": "mode", "flag": "--mode", "type": "select", "default": "token",
     "category": "mode", "label": "优化模式",
     "description": "Token 优先追求最大压缩率，Cache 优先则牺牲部分压缩率换取更高的语义缓存命中",
     "options": [{"value": "token", "label": "Token 优先（最大压缩）"},
                 {"value": "cache", "label": "Cache 优先（提高缓存命中）"}]},
    {"key": "port", "flag": "--port", "type": "number", "default": "8787",
     "category": "mode", "label": "监听端口",
     "description": "Headroom 代理监听的端口号，修改后需更新 ANTHROPIC_BASE_URL 中的端口"},
    {"key": "workers", "flag": "--workers", "type": "number", "default": "1",
     "category": "mode", "label": "工作进程数",
     "description": "并发处理请求的工作进程数，多核机器可适当调高以提升吞吐"},
    {"key": "no-optimize", "flag": "--no-optimize", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用压缩（透传模式）",
     "description": "开启后 Headroom 仅转发请求不做任何压缩，适用于排查压缩导致的兼容问题"},
    {"key": "no-cache", "flag": "--no-cache", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用语义缓存",
     "description": "关闭语义缓存，每个请求都会完整走压缩流程，不会命中缓存"},
    {"key": "no-rate-limit", "flag": "--no-rate-limit", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用速率限制",
     "description": "关闭请求频率限制，高并发场景下可能触发上游 API 限流"},
    {"key": "code-aware", "flag": "--code-aware", "type": "bool", "default": False,
     "category": "optimization", "label": "启用 AST 代码压缩",
     "description": "对代码内容做 AST 级别的智能压缩，比通用压缩更节省代码类 tokens"},
    {"key": "intercept-tool-results", "flag": "--intercept-tool-results", "type": "bool", "default": False,
     "category": "optimization", "label": "拦截 Tool Results",
     "description": "拦截并压缩 Claude Code 的工具执行结果，减少长输出对上下文的占用"},
    {"key": "code-graph", "flag": "--code-graph", "type": "bool", "default": False,
     "category": "optimization", "label": "启用代码图谱智能",
     "description": "利用代码图谱分析调用关系，更精准地判断哪些上下文可以压缩"},
    {"key": "memory", "flag": "--memory", "type": "bool", "default": False,
     "category": "memory", "label": "启用持久记忆",
     "description": "启用后 Headroom 会记住跨会话的关键上下文，避免重复向 Claude 发送"},
    {"key": "memory-storage", "flag": "--memory-storage", "type": "select", "default": "project",
     "category": "memory", "label": "记忆存储方式",
     "description": "Project 按项目目录隔离记忆，User 按用户隔离，Global 全局共享",
     "options": [{"value": "project", "label": "Project（按项目隔离）"},
                 {"value": "user", "label": "User（按用户隔离）"},
                 {"value": "global", "label": "Global（全局共享）"}]},
    {"key": "memory-top-k", "flag": "--memory-top-k", "type": "number", "default": "10",
     "category": "memory", "label": "注入记忆条数",
     "description": "每次请求最多向上下文注入多少条历史记忆，调高可提供更多上下文但增加 tokens"},
    {"key": "learn", "flag": "--learn", "type": "bool", "default": False,
     "category": "memory", "label": "启用流量学习",
     "description": "分析流量模式自动优化压缩策略，长期运行能显著提升压缩效果"},
    {"key": "anthropic-api-url", "flag": "--anthropic-api-url", "type": "text", "default": "",
     "category": "backend", "label": "自定义 API 地址",
     "description": "覆盖 Headroom 上游的 Anthropic API 地址，可用于指向 DeepSeek 兼容接口",
     "placeholder": "https://api.deepseek.com/anthropic"},
    {"key": "backend", "flag": "--backend", "type": "select", "default": "anthropic",
     "category": "backend", "label": "API 后端",
     "description": "选择上游 API 后端：Anthropic 直连、AWS Bedrock 或 OpenRouter",
     "options": [{"value": "anthropic", "label": "Anthropic 直连"},
                 {"value": "bedrock", "label": "AWS Bedrock"},
                 {"value": "openrouter", "label": "OpenRouter"}]},
    {"key": "region", "flag": "--region", "type": "text", "default": "us-west-2",
     "category": "backend", "label": "云区域（Bedrock/Vertex）",
     "description": "AWS Bedrock 或 Google Vertex AI 的服务区域，如 us-west-2、us-east-1"},
    {"key": "budget", "flag": "--budget", "type": "number", "default": "",
     "category": "log", "label": "每日预算上限（USD）",
     "description": "每日 API 消费预算上限（美元），达到上限后将拒绝新请求"},
    {"key": "no-telemetry", "flag": "--no-telemetry", "type": "bool", "default": False,
     "category": "log", "label": "关闭匿名遥测",
     "description": "关闭向 Headroom 项目发送匿名使用统计数据"},
    {"key": "log-file", "flag": "--log-file", "type": "text", "default": "",
     "category": "log", "label": "日志文件路径",
     "description": "将 Headroom 日志输出到指定文件，留空则输出到容器标准输出"},
    {"key": "log-messages", "flag": "--log-messages", "type": "bool", "default": False,
     "category": "log", "label": "记录完整消息体",
     "description": "在日志中记录完整的请求和响应消息体，调试时有用但会大量增加日志"},
]


def docker_cmd(*args, capture=True):
    cmd = [DOCKER_PATH] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=capture, text=True,
                           encoding="utf-8", errors="replace", timeout=30)
        if capture:
            out = r.stdout.strip() if r.stdout else ""
            err = r.stderr.strip() if r.stderr else ""
            return out, err, r.returncode
        return "", "", r.returncode
    except FileNotFoundError:
        return "", "docker not found at " + DOCKER_PATH, -1
    except subprocess.TimeoutExpired:
        return "", "command timed out", -1


def get_container_status():
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
    try:
        r = requests.get(f"{HEADROOM_API}/health", timeout=5)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except requests.RequestException as e:
        return {"error": str(e)}


def get_headroom_stats():
    try:
        r = requests.get(f"{HEADROOM_API}/stats", timeout=5)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}"}
    except requests.RequestException as e:
        return {"error": str(e)}


def check_docker_available():
    """检查 Docker CLI 是否可用"""
    _, stderr, rc = docker_cmd("info", "--format", "{{.ServerVersion}}")
    return rc == 0


_headroom_warmed_up = False

def warmup_headroom_litellm():
    """发送空请求到 /v1/messages 触发 LiteLLM 预热，消除首次请求的 40s 延迟"""
    global _headroom_warmed_up
    if _headroom_warmed_up:
        return
    try:
        requests.post(
            f"{HEADROOM_API}/v1/messages",
            json={"model": "claude-sonnet-4-6", "max_tokens": 1, "messages": [{"role": "user", "content": ""}]},
            headers={"x-api-key": "warmup", "anthropic-version": "2023-06-01"},
            timeout=60,
        )
    except requests.RequestException:
        pass  # 预热失败很正常（无有效 key），但 LiteLLM 已被触发加载
    _headroom_warmed_up = True


def read_profile():
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        return f"# Error reading profile: {e}"


def write_profile(content):
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def get_headroom_config_from_inspect():
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
    # Docker 选项（镜像名前）
    docker_opts = ["run", "-d", "--name", HEADROOM_CONTAINER,
                   "--restart", "unless-stopped",
                   "-p", "8787:8787",
                   "-v", f"{os.path.expanduser('~')}\\.headroom:/root/.headroom",
                   "-e", "HF_ENDPOINT=https://hf-mirror.com"]

    env_vars = {}
    if params.get("anthropic-api-url"):
        env_vars["ANTHROPIC_TARGET_API_URL"] = params["anthropic-api-url"]

    bool_on = {"memory", "code-aware", "code-graph", "learn", "intercept-tool-results",
               "no-telemetry", "log-messages"}
    bool_off = {"no-optimize", "no-cache", "no-rate-limit"}

    # Headroom 容器参数（镜像名后，作为 CMD 参数传入）
    headroom_args = []
    for p in CONFIG_PARAMS:
        key = p["key"]
        if key in params:
            val = params[key]
            if p["type"] == "bool":
                if key in bool_on and str(val).lower() in ("true", "1", "on", "yes"):
                    headroom_args.append(p["flag"])
                elif key in bool_off and str(val).lower() in ("true", "1", "on", "yes"):
                    headroom_args.append(p["flag"])
            elif p["type"] in ("text", "number", "select"):
                if val is not None and str(val).strip():
                    headroom_args.append(p["flag"])
                    headroom_args.append(str(val).strip())

    for k, v in env_vars.items():
        docker_opts.extend(["-e", f"{k}={v}"])

    return docker_opts + ["ghcr.io/chopratejas/headroom:latest"] + headroom_args


def recreate_container(params):
    docker_cmd("stop", HEADROOM_CONTAINER, capture=False)
    docker_cmd("rm", HEADROOM_CONTAINER, capture=False)
    run_args = build_docker_run_args(params)
    stdout, stderr, rc = docker_cmd(*run_args)
    if rc != 0:
        return {"success": False, "error": stderr or stdout, "returncode": rc}
    time.sleep(3)
    status = get_container_status()
    return {"success": status["running"], "container": status, "output": stdout}


# ─── Routes ────────────────────────────────────────────────────────────────

@app.route("/api/startup/status")
def api_startup_status():
    """返回启动就绪状态，供 Splash 页面轮询"""
    docker_available = check_docker_available()

    if not docker_available:
        return jsonify({
            "phase": "docker_unavailable",
            "docker_available": False,
            "container_running": False,
            "headroom_ready": False,
            "detail": "Docker Desktop 未运行或未安装",
        })

    container = get_container_status()
    container_running = container.get("running", False)

    if not container_running and container.get("status") == "not_found":
        return jsonify({
            "phase": "container_missing",
            "docker_available": True,
            "container_running": False,
            "headroom_ready": False,
            "detail": "Headroom 容器不存在，正在创建...",
        })

    if not container_running:
        return jsonify({
            "phase": "container_stopped",
            "docker_available": True,
            "container_running": False,
            "headroom_ready": False,
            "detail": "Headroom 容器已停止，正在启动...",
        })

    health = get_headroom_health()
    headroom_ready = health.get("status") == "healthy" if isinstance(health, dict) else False

    if headroom_ready and not _headroom_warmed_up:
        threading.Thread(target=warmup_headroom_litellm, daemon=True).start()

    detail = "Headroom 服务就绪" if headroom_ready else "等待 Headroom 服务初始化..."

    return jsonify({
        "phase": "ready" if headroom_ready else "waiting_headroom",
        "docker_available": True,
        "container_running": True,
        "headroom_ready": headroom_ready,
        "health": health if isinstance(health, dict) else {},
        "detail": detail,
    })


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/assets/<path:filename>")
def serve_asset(filename):
    return send_from_directory("static", filename)


@app.route("/api/config/pricing")
def api_config_pricing():
    """返回 DeepSeek V4 定价信息"""
    return jsonify(DEEPSEEK_PRICING)


@app.route("/api/stats")
def api_stats():
    container = get_container_status()
    health = get_headroom_health() if container["running"] else {"error": "container not running"}
    stats = get_headroom_stats() if container["running"] else {"error": "container not running"}
    model_costs = compute_costs(stats) if isinstance(stats, dict) else {}
    return jsonify({"container": container, "health": health, "stats": stats, "model_costs": model_costs})


@app.route("/api/logs")
def api_logs():
    lines = request.args.get("lines", "100")
    stdout, stderr, rc = docker_cmd("logs", HEADROOM_CONTAINER, "--tail", lines, "--timestamps")
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
    anthro_match = re.search(r'\$env:ANTHROPIC_BASE_URL\s*=\s*"([^"]+)"', content)
    profile_url = anthro_match.group(1) if anthro_match else ""
    system_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    # 读取 Claude Code settings.json（最高优先级）
    claude_url = ""
    try:
        if os.path.exists(CLAUDE_SETTINGS_PATH):
            with open(CLAUDE_SETTINGS_PATH, "r", encoding="utf-8") as f:
                claude_settings = json.load(f)
            claude_url = (claude_settings.get("env") or {}).get("ANTHROPIC_BASE_URL", "")
    except Exception:
        pass
    current_url = claude_url or system_url or profile_url
    return jsonify({
        "profile_content": content,
        "anthropic_base_url": current_url,
        "env_var": system_url,
        "profile_url": profile_url,
        "claude_settings_url": claude_url,
        "docker_path": DOCKER_PATH,
        "last_modified": os.path.getmtime(PROFILE_PATH) if os.path.exists(PROFILE_PATH) else None,
    })


@app.route("/api/config/system", methods=["POST"])
def api_config_system_post():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "无数据"}), 400

    action = data.get("action", "update_url")

    if action == "toggle_route":
        route = data.get("route", "")
        if route == "headroom":
            new_url = "http://localhost:8787"
        elif route == "direct":
            new_url = "https://api.deepseek.com/anthropic"
        else:
            return jsonify({"success": False, "error": "未知路由"}), 400

    elif action == "update_url":
        new_url = data.get("anthropic_base_url", "")
        content = read_profile()

        # 写入 PowerShell profile（PS 用户可用）
        if re.search(r'\$env:ANTHROPIC_BASE_URL\s*=', content):
            content = re.sub(
                r'\$env:ANTHROPIC_BASE_URL\s*=\s*"[^"]*"',
                f'$env:ANTHROPIC_BASE_URL = "{new_url}"',
                content,
            )
        else:
            headroom_section = "# Headroom proxy — Claude Code context compression\n"
            if headroom_section in content:
                content = content.replace(
                    headroom_section,
                    headroom_section + f'$env:ANTHROPIC_BASE_URL = "{new_url}"\n',
                )
            else:
                content = f'{headroom_section}$env:ANTHROPIC_BASE_URL = "{new_url}"\n\n{content}'
        write_profile(content)

        # 写入系统环境变量（cmd 用户可用）
        try:
            subprocess.run(
                ["setx", "ANTHROPIC_BASE_URL", new_url],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:
            pass

        # 写入 Claude Code settings.json（优先级最高）
        try:
            if os.path.exists(CLAUDE_SETTINGS_PATH):
                with open(CLAUDE_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    claude_settings = json.load(f)
            else:
                claude_settings = {}
            if "env" not in claude_settings:
                claude_settings["env"] = {}
            if new_url:
                claude_settings["env"]["ANTHROPIC_BASE_URL"] = new_url
            elif "ANTHROPIC_BASE_URL" in claude_settings.get("env", {}):
                del claude_settings["env"]["ANTHROPIC_BASE_URL"]
            os.makedirs(os.path.dirname(CLAUDE_SETTINGS_PATH), exist_ok=True)
            with open(CLAUDE_SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(claude_settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # 当前进程也设上，Flask 自己的 subprocess 能读到
        os.environ["ANTHROPIC_BASE_URL"] = new_url

        return jsonify({"success": True, "message": "已更新，立即生效（下次 Claude Code 请求）"})

    elif action == "update_profile":
        new_content = data.get("profile_content", "")
        write_profile(new_content)
        return jsonify({"success": True, "message": "profile.ps1 已更新"})

    return jsonify({"success": False, "error": f"未知操作: {action}"}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
