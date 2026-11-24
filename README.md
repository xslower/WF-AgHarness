# Agent Harness

**浏览器里的 AI Agent 工作台**：一个对话框，驱动文件操作、网页搜索、代码执行与工作流编排。本地运行，数据不出你的机器。

> 下载即用，无需安装任何环境。[Releases](../../releases) 获取最新版本。

---

## 一、怎么用

### Windows

1. 下载 `harness-0.1.0-windows-x86_64.zip`
2. 解压到任意目录
3. 双击 `Harness.exe`，右下角出现托盘图标
4. 右键托盘图标选 **Open WF-AgHarness**，浏览器窗口自动打开
5. 开始对话

![托盘菜单](docs/screenshots/windows-tray.png)

- 退出：右键托盘 **Exit**（不要直接关窗口）
- 想从头开始：删除包里的 `data` 文件夹

### Linux

1. 下载 `harness-0.1.0-linux-x86_64.tar.gz`
2. 解压，双击 `start.sh` 或在终端运行它
3. 浏览器窗口自动打开，开始对话

![主界面](docs/screenshots/main-window.png)

- 退出：Ctrl+C
- 想从头开始：删除包里的 `data` 文件夹

---

## 二、能做什么

### 对话即操作

用自然语言让 AI 帮你干活。拖入文件、文件夹直接当上下文，AI 自动理解。

![对话界面](docs/screenshots/chat.png)

- 读写文件、搜索代码、批量改名
- 历史对话自动保存，随时翻出来继续

### 工作流编辑器

不想每次打字？把常用任务拖拽搭成流程图，一次编排，反复使用。

![工作流](docs/screenshots/workflow.png)

内置模板：代码审查、文档生成、数据分析等，开箱即用。

### 支持多家 AI 模型

OpenAI、Claude、DeepSeek、通义千问、本地 Ollama 等，统一界面一键切换，Token 用量一目了然。

![模型配置](docs/screenshots/models.png)

### 联网搜索与网页抓取

内置浏览器引擎，能打开需要登录的页面、抓取 JS 渲染后的内容，自动转成干净文本。

![网页抓取](docs/screenshots/crawler.png)

### 插件扩展

就像手机装 App，按需加载工具、技能包、外部服务。会写代码可以自己开发。

![插件管理](docs/screenshots/plugins.png)

### 安全可控

AI 能做什么、不能做什么，你说了算——每个工具都可以设为"允许""需确认""禁止"。所有操作留痕，可追溯。

![策略配置](docs/screenshots/policy.png)

---

## 三、许可

Apache-2.0 开源，可自由使用、修改、商用。详见 [LICENSE](LICENSE)。

---

## 四、商业服务

需要开箱即用的成品或专业服务？

- **垂直 AI Bot**：客服、文档问答、销售辅助
- **私有化部署**：多租户、权限隔离、内网离线
- **定制开发**：插件、工作流、系统对接
- **技术培训**：架构评审、二次开发辅导

在 [Issues](https://github.com/xslower/WF-AgHarness/issues) 标注"商务咨询"，或关注下方渠道联系我们。

---

## 五、关注我们

<div align="center">

| 视频号 | 公众号 | 抖音 |
|:---:|:---:|:---:|
| <img src="docs/qr/shipin.jpg" width="220"> | <img src="docs/qr/gongzhong.jpg" width="220"> | <img src="docs/qr/douyin.jpg" width="220"> |

</div>

---

*觉得有用？点个 Star。*
