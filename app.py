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
     "options": [{"value": "token", "label": "Token 优先（最大压缩）"},
                 {"value": "cache", "label": "Cache 优先（提高缓存命中）"}]},
    {"key": "port", "flag": "-p", "type": "number", "default": "8787",
     "category": "mode", "label": "监听端口"},
    {"key": "workers", "flag": "--workers", "type": "number", "default": "1",
     "category": "mode", "label": "工作进程数"},
    {"key": "no-optimize", "flag": "--no-optimize", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用压缩（透传模式）"},
    {"key": "no-cache", "flag": "--no-cache", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用语义缓存"},
    {"key": "no-rate-limit", "flag": "--no-rate-limit", "type": "bool", "default": False,
     "category": "optimization", "label": "禁用速率限制"},
    {"key": "code-aware", "flag": "--code-aware", "type": "bool", "default": False,
     "category": "optimization", "label": "启用 AST 代码压缩"},
    {"key": "intercept-tool-results", "flag": "--intercept-tool-results", "type": "bool", "default": False,
     "category": "optimization", "label": "拦截 Tool Results"},
    {"key": "code-graph", "flag": "--code-graph", "type": "bool", "default": False,
     "category": "optimization", "label": "启用代码图谱智能"},
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
     "category": "memory", "label": "启用流量学习"},
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
    {"key": "budget", "flag": "--budget", "type": "number", "default": "",
     "category": "log", "label": "每日预算上限（USD）"},
    {"key": "no-telemetry", "flag": "--no-telemetry", "type": "bool", "default": False,
     "category": "log", "label": "关闭匿名遥测"},
    {"key": "log-file", "flag": "--log-file", "type": "text", "default": "",
     "category": "log", "label": "日志文件路径"},
    {"key": "log-messages", "flag": "--log-messages", "type": "bool", "default": False,
     "category": "log", "label": "记录完整消息体"},
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
    args = ["run", "-d", "--name", HEADROOM_CONTAINER,
            "--restart", "unless-stopped",
            "-p", "8787:8787",
            "-v", f"{os.path.expanduser('~')}/.headroom:/root/.headroom"]

    env_vars = {}
    if params.get("anthropic-api-url"):
        env_vars["ANTHROPIC_TARGET_API_URL"] = params["anthropic-api-url"]

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

    for k, v in env_vars.items():
        args.extend(["-e", f"{k}={v}"])

    args.append("ghcr.io/chopratejas/headroom:latest")
    return args


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
