# 插件开发指南

面向插件作者。读完你能从零写出一个可登记的插件包。契约稳定，按本文写即可，无需依赖内部实现细节。

## 0. 先判断要不要写插件

| 你想做的事 | `kinds` | 要写代码吗 |
|---|---|---|
| 加一个模型服务商预设（baseUrl / 环境变量名） | `provider` | 否，写在 `plugin.yaml` 的 `providers` 段 |
| 打包一组 `SKILL.md` 技能 | `skill_bundle` | 否，放 `skills/<name>/SKILL.md` |
| 加一条工作流 | `workflow` | 否，放 `workflows/<name>.json` |
| 声明 MCP 服务器 | `mcp_server` | 否，放包内 `mcp.json` 的 `servers` 段 |
| 加一个工具 | `tool` | 是，`tools/*.py` 或 `tools/<name>/`，必须有 `register(reg)` |
| 加后端接口 + 前端页面 | `api` | 是，`api/*.py` 的 `handle(req, host)` + 静态资源 |

`kinds` 可任意组合：一个包可同时是 workflow + tool + skill + api + mcp。

约定：**当前为 v3「就地登记制」**——安装 = 校验 + 登记，系统**不复制**你的文件；卸载只摘登记，**不删文件**。包目录就是最终位置，改包内文件立即生效（按 mtime 重新加载）。不支持老版的 `manifest.json` / `plugin.py`。

---

## 1. 包结构

```
<project>/.agent/plugins/my-plugin/     # 项目插件放这里；全局型插件放仓库 plugins/<id>/
├── plugin.yaml                        # 必需
├── workflows/daily.json
├── tools/my_tool.py                   # 单文件工具：必须有 register(reg)
├── tools/search_bundle/               # 目录型工具（多文件）
│   ├── tool.yaml                      # 入口由这里指定
│   ├── main.py                        # 入口：必须有 register(reg)
│   └── helper.py                      # 同目录辅助模块，普通 import
├── skills/pdf-read/SKILL.md
├── api/router.py                      # async def handle(req, host)
├── index.html                         # 静态入口（默认）
├── static/app.js                      # html/js/css/图片，位置随意
├── mcp.json                           # {"servers": {...}}
└── README.md
```

**静态资源零登记**：`/api/plugin?id=<id>&static=<相对包根路径>` 直接回吐包内文件。

`plugin.yaml`：

```yaml
id: my-plugin                 # 小写字母/数字/._-，2-64
name: 我的插件
version: 1.0.0
kinds: [workflow, tool, skill_bundle, mcp_server, api]
desc: 一句话说明
entry: index.html             # 可选：静态入口（相对包根，默认 index.html）

providers:                    # 可选：provider 只是数据
  - id: my-provider
    kind: env_preset
    base_url: https://api.example.com/v1
    env_keys: [EXAMPLE_KEY]

config:                       # 可选：系统渲染成配置页；参数名 → 默认值/声明
  api_base: {label: 上游地址, type: string, default: https://api.example.com, required: true}
```

---

## 2. 工具：`register(reg)`

单文件工具（`<包>/tools/my_tool.py`）最小示例：

```python
def register(reg):
    reg.tool("my_search", "按关键词搜索", {
        "query": {"type": "string", "description": "关键词"},
        "limit": {"type": "integer", "description": "返回条数上限"},
    }, my_search)

def my_search(query: str, limit: int = 20, ctx=None) -> str:
    return f"search {query} limit={limit}"
```

- `ctx` 由框架注入，**不要**写进 `params`。
- 工具名与内置工具同名 → 拒绝注册（不静默覆盖）。
- 一个 `register(reg)` 可注册任意多个工具。

### 2.1 目录型工具（多文件）

多文件时放一个目录并写 `tool.yaml`：

```yaml
entry: main.py          # 必填：目录内相对路径，必须 .py、不得越出目录
scope: local            # local（默认，项目内可见）/ global（系统级）
                        # 别名 project=local、system=global
name: 搜索工具包        # 可选：显示名
desc: 多个搜索工具的合集
version: 1.0.0
tools:                  # 可选：工具名 + 可选描述
  - name: web_search_pro
  - name: web_fetch_pro
    desc: 按 URL 取正文
```

入口 `main.py`：

```python
# 同目录其它 .py 用普通 import，不做相对导入
from helper import fetch

def register(reg):
    reg.tool("web_search_pro", "搜索", {"q": {"type": "string"}}, search)
    reg.tool("web_fetch_pro", "", {"url": {"type": "string"}}, fetch)
```

**配置归属**：

- **插件包内的工具**没有自己的配置：配置统一写在 `plugin.yaml` 的 `config` 段，工具里用 `reg.config("名字")` 读。
- **独立工具**（`<项目>/.agent/tools/<name>/`）的 `tool.yaml` 里可写 `config`，由主页「工具」区配置。
- 单文件工具不支持配置；要配置就改成目录形态。
- 插件内工具的 `tool.yaml` 里写 `config` 会**拒装**。

`config` 字段写法：`key/label/type/default/required/min/max/options`，嵌套参数名拍平成 `A.B`（最多 3 层）。需要 label / options 时值写成声明：

```yaml
config:
  api_base: {label: 接口地址, type: string, default: https://example.com, required: true}
  model: {label: 模型, type: string, options: [a, b], default: a}
```

### 2.2 密钥（只写两样东西、只调两个方法）

- 第三方 / 生图服务 key（如 agnes、硅基、moss 等）：在 `config` 段写 `type: key`（`secret` 同实现），系统加密存储，工具用 `reg.config(name)` 取**明文**：

  ```yaml
  config:
    moss_key: {label: Moss Key, type: key, required: true}
  ```

  ```python
  key = reg.config("moss_key")   # 明文；库里是 enc:v1: 密文
  ```

- 系统设置页里的 LLM provider key：在 `plugin.yaml` 写 `requested_provider_keys: [前缀]`，安装时逐项许可；工具用 `reg.provider_key(name)` 取**数组**（一个前缀命中所有同前缀账号，如 `moss` 命中 `moss-185` / `moss173`）：

  ```python
  keys = reg.provider_key("moss")   # 数组；无匹配返回 []
  ```

别把生图 key 写进 `requested_provider_keys`，也别塞进系统 provider。密钥加密、许可、存储路径都是系统概念，工具作者只传字段名。

### 2.3 工具级联（可选，只支持 web / asr / ocr / gen_image）

给某个系统工具提供备选实现，不让模型看到两个工具：

```python
def register(reg):
    async def paid(query: str = "", limit: int = 5, ctx=None) -> str:
        ...  # 失败返回含真值 error 的 JSON 或 {"ok": false}
    reg.cascade("web", paid, order="after")   # after=系统失败后用我；before=我先
```

- 只能**全局插件**（`scope: global`）声明级联，项目插件声明会被忽略。
- 声明后本工具不再独立暴露，由系统工具内部合并调用。
- 失败判据：返回 JSON 含真值 `error`，或 `ok=false`。

### 2.4 工具 schema 三级来源

1. `params` 每个参数都有 `description` → 原样使用；
2. 声明不全 → 登记时用子队列模型读源码补全 schema（需模型可用）；
3. 模型不可用 → 从函数签名 + 类型注解 + docstring 的 `Args:` 段推导。

签名推导要求每个参数**要么有类型注解、要么有默认值**。任一项不满足且模型不可用 → 整包拒装。登记时强制校验：文件能 import、有可调用 `register(reg)`、每个工具参数 schema 可推导。

---

## 3. 插件 API：`api/router.py`

```python
async def handle(req, host):
    """req: {method, path, query, headers, body, json}；host 是受限 SDK。
    返回 dict → JSON；str → text；(status, dict) → 指定状态码；async generator → SSE。"""
    if req["path"] == "/echo":
        return {"you_sent": host.json(req)}
    return 404, {"error": "no route"}
```

- URL 统一前缀：`/api/plugin?id=<id>&path=<...>` 转给 `handle`；`&static=<相对包根路径>` 回吐资源。
- 宿主 SDK 白名单（`host`）：`config` / `json` / `run_workflow` / `call_tool` / `mcp` / `emit` / `log` / **`data`**。不提供裸文件 / 裸数据库 / 裸 HTTP 端口；`call_tool` 必经策略引擎。

### 3.1 现场模板注入与静态资源

回吐 html/js/css 时替换 `{{base}}`（= `/api/plugin?id=<id>`）、`{{id}}`、`{{project}}`；HTML 额外注入 `window.plugin`。二进制原样直出，全部 `no-store`。

```html
<img src="{{base}}&static=static/pic.png">
<script>
  fetch("{{base}}&path=save", {method: "POST", body: JSON.stringify({score: 1})});
</script>
```

`static=` 是相对**包根**的路径，不是 `api/static/`。文本白名单后缀：html/js/css/json/svg/txt（其它后缀不替换 `{{base}}`，可在 JS 里读 `window.plugin.base`）。

### 3.2 `host.data` 存进度

```python
async def handle(req, host):
    if req["path"] == "/save":
        host.data.set("progress", host.json(req)["score"])
        return {"saved": True}
    return {"progress": host.data.get("progress")}
```

方法：`get/set/delete/keys`。同一份数据在工作流 code 节点里用注入的 `plugin.data` 读写（preamble 已注入，不用 import）：

```python
plugin.data.set("progress", plugin.data.get("progress", 0) + 1)
```

安装 / 卸载后系统主动 reload，handler 即时生效 / 失效，无需重启。

---

## 4. 登记、卸载与开发模式

| 动作 | 入口 | 发生什么 |
|---|---|---|
| 登记包 | 项目主页「登记」或 `POST /api/plugins/install` | 校验格式 → 写登记 → 出现在项目主页插件区 |
| 登记独立 skill / tool | `POST /api/plugins/adopt` | 只写登记行，文件原位不动 |
| 卸载 | 项目主页 🗑 或 `DELETE /api/plugins/installed/{id}` | 只摘登记行，**不删文件** |
| 开发模式 | 主页「扫描」后的未安装区 / 插件独立页 | 校验失败也可见，列出错误；改完点「重新登记」 |

**可见性 ≠ 生效**：未登记的包能打开、能编辑，但能力不加载。插件永远不是项目：不开会话、不进侧栏树。

---

## 5. 出站切换插件（高级，接管 provider 出站）

一个 pluginId 只有一个接管者（后注册胜出）。三步：

1. 包内 `provider.py:provide(host)` 返回标准 provider 数据；key 建议从环境变量读（`os.environ.get(env_key)`），`host.config()` 读配置。标准 OpenAI 协议**不要**给 `models`（系统自动拉）。
2. `plugin.yaml` 写 `kinds: [outbound_switch]` + `outbound_switches:` 段：

   ```yaml
   id: my-proxy
   kinds: [outbound_switch]
   mode: release
   outbound_switches:
     - provider: my-upstream
       setup: switch         # outbound/switch.py
       handler: handle
   ```

3. `outbound/<setup>.py:handle(req)` 收 `OutboundRequest`：返回 `None` 交还默认 adapter（可先改 `req.headers` / `req.body`），或返回 `OutboundResponse` 完全接管。**抛错 / 返回 None 不会中断请求**，系统 fallback 默认 adapter。

坑：不要给 `provider.py` 写 `id` / `pluginId`（系统字段，忽略）；按 `Provider.pluginId` 命中，不按名字（名字可改）。

---

## 6. 排查对照表

| 症状 | 原因 | 怎么修 |
|---|---|---|
| 包不出现在「已登记插件」 | 校验没过（tools 缺 register / 签名推不出） | 看开发模式卡片的错误，改完重新登记 |
| 工具没出现 | 没登记，或与内置工具同名 | 重新登记；改名 |
| api 404 | 未登记 / `api/*.py` 没有 `handle` / URL 少了 `&path=` | 重新登记；补 handle；用 `{{base}}&path=...` |
| 静态 404 / 图片裂 | `static=` 是相对**包根**的路径 | 改成 `{{base}}&static=static/pic.png` |
| `{{base}}` 没替换 | 后缀不在文本白名单 | 换后缀，或读 `window.plugin.base` |
| 工作流看不到 | 主页只列项目自己的 | 进插件独立页（插件行「详情」） |
| 改了 `tools/*.py` 没生效 | 模块缓存 | 系统按 mtime 自动重载；仍不行就重新登记 |

---

## 7. 限制与约定

- **依赖不代装**：`plugin.yaml` 的 `env.requires` 只作展示；系统禁 pip/npm install。插件代码只用 Python 标准库 + 宿主 SDK 提供能力。
- 插件不碰 FastAPI app / lifespan / 中间件，不注册全局能力（项目作用域）。
- 插件包内不需要 `.agent/`；包不是项目，不开会话。

写一个最小插件的最小步骤：① 建 `plugin.yaml`（id/name/version/kinds/desc）；② 按 kind 放文件（工具必须有 `register(reg)` 且参数可推导）；③ 项目主页点「登记」；④ 失败看开发模式错误，改完重试。祝你开发顺利。
