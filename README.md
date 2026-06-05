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
