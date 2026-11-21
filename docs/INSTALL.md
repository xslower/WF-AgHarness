# 安装与部署

## 方式 A：开箱包（推荐）

从 [Releases](../../releases) 下载对应平台的包，解压即用，无需预装 Python / Node / 任何依赖。

```bash
# Linux / macOS
tar xzf harness-0.1.0-linux-x86_64.tar.gz
cd harness-0.1.0-linux-x86_64
./start.sh
# 浏览器打开 http://127.0.0.1:8001
```

- 改端口：`HARNESS_PORT=9000 ./start.sh`
- 停止：Ctrl+C
- 数据位置：包内 `data/`；重置数据删该目录即可。
- 首次启动无需联网（自带 Python 运行环境与 Chromium）。

## 方式 B：源码运行

需要 Python 3.11+（推荐 3.12）。

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

浏览器打开 `http://127.0.0.1:8001`。后端已托管前端产物；若前端目录为空需先构建：

```bash
cd frontend && npm install && npm run build
```

> 源码仓库默认不含 `frontend/dist`（构建产物），开箱包内已含。

## 方式 C：Docker

```bash
# 仓库未提供预构建镜像；先用源码构建：
# docker build -t agent-harness .
# docker run -d -p 8001:8001 -v $PWD/data:/app/data agent-harness:latest
```

## 配置

- LLM provider：首次在 Web 界面「设置」里添加模型服务商的 baseUrl 与 API Key。
- 数据目录：源码运行可通过环境变量 `HARNESS_DATA_DIR` 指定。
- 详细配置项见 Web 界面设置页。

## 升级

- 开箱包：下载新包解压到新目录，`data/` 拷过去即完成迁移。
- 源码：`git pull` 后重装依赖；数据结构变更会在启动时自动迁移。

## 备份

备份 `data/` 目录即可（含会话、事件、配置、知识库索引）。建议停止服务后备份。
