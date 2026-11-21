
import type { NodeCatalogItem } from "../../kernel/api";
import { Icon, nodeIcon, type IconName } from "../../kernel/ui/icons";
import { PanelClose } from "./PanelClose";

export interface PaletteField {
  key: string;
  label: string;
  kind: "text" | "textarea" | "code" | "select" | "number" | "boolean" | "model";
  ph?: string;
  opts?: string[];
  required?: boolean;
}

interface PaletteItem {
  type: string;
  label: string;
  desc: string;
  icon: string;
  group?: string;
  preset?: Record<string, string>;  
  fields: PaletteField[];
}

const TOOL_FIELD: PaletteItem["fields"] = [
  { key: "tool", label: "工具名", kind: "text", ph: "read_file / grep / skill / ..." },
  { key: "argsJson", label: "参数 JSON（值支持 ${}）", kind: "textarea", ph: '{"path": "${s1}"}' },
];


const PALETTE: { group: string; items: PaletteItem[] }[] = [
  {
    group: "LLM",
    items: [
      { type: "llm", label: "LLM 对话", icon: "robot", desc: "模型选择与会话一致，支持 ${变量}",
        fields: [
          { key: "prompt", label: "提示词（${inputs.x} / ${节点id}）", kind: "textarea", ph: "翻译成英文：${inputs.input}" },
          { key: "format", label: "输出格式", kind: "select", opts: ["text", "json", "list"] },
          { key: "jsonFields", label: "JSON 字段（逗号分隔，如 title,items；下游用 ${节点id.字段}）", kind: "text", ph: "title, summary" },
          { key: "model", label: "模型（父队列 / 子队列 / 总结队列 / 指定模型）", kind: "model", ph: "留空=总结队列" },
        ] },
      { type: "subagent", label: "子 Agent", icon: "puzzle", desc: "独立上下文，默认走总结队列，可指定模型",
        fields: [{ key: "task", label: "任务描述", kind: "textarea" },
                 { key: "model", label: "模型（父队列 / 子队列 / 总结队列 / 指定模型）", kind: "model", ph: "留空=总结队列" }] },
      { type: "handoff", label: "交接输出", icon: "export", desc: "LLM调用时返回调用方；手动运行写报告", fields: [] },
    ],
  },
  {
    group: "文件 IO",
    items: [
      { type: "tool", label: "读文件", icon: "book", preset: { tool: "f_read" }, desc: "读取文件内容",
        fields: [{ key: "argsJson", label: "参数 JSON", kind: "textarea", ph: '{"path": "a.txt", "lines": "1,50"}' }, { key: "tool", label: "工具名", kind: "text" }] },
      { type: "tool", label: "写文件", icon: "file-text", preset: { tool: "f_write" }, desc: "写入/按行插入/按行区间替换",
        fields: [{ key: "argsJson", label: "参数 JSON", kind: "textarea", ph: '{"path": "out.md", "content": "${s1}"}' }, { key: "tool", label: "工具名", kind: "text" }] },
      { type: "tool", label: "改文件", icon: "pencil", preset: { tool: "f_replace" }, desc: "按内容替换一处",
        fields: [{ key: "argsJson", label: "参数 JSON", kind: "textarea", ph: '{"path": "a.txt", "old": "原文", "new": "新文"}' }, { key: "tool", label: "工具名", kind: "text" }] },
      { type: "tool", label: "搜文件名", icon: "search", preset: { tool: "search_files" }, desc: "glob 搜索 / 不传 pattern 列目录",
        fields: [{ key: "argsJson", label: "参数 JSON", kind: "textarea", ph: '{"pattern": "*.py"} 或 {"path": "."}' }, { key: "tool", label: "工具名", kind: "text" }] },
      { type: "tool", label: "内容检索", icon: "search", preset: { tool: "grep" }, desc: "多关键词搜内容（默认字面量）",
        fields: [{ key: "argsJson", label: "参数 JSON", kind: "textarea", ph: '{"key": ["def main", "TODO"], "regex": false}' }, { key: "tool", label: "工具名", kind: "text" }] },
    ],
  },
  {
    group: "代码",
    items: [
      { type: "exec", label: "执行命令", icon: "bolt", desc: "shell 命令（受安全策略约束）",
        fields: [{ key: "command", label: "命令", kind: "text", ph: "python script.py" },
          { key: "timeout", label: "超时（秒，0=默认 600）", kind: "number", ph: "600" }] },
      { type: "op", label: "算子", icon: "sparkle", desc: "调项目里的领域算子（<项目>/.agent/ops），不经 shell 桥",
        fields: [
          { key: "op", label: "算子名", kind: "text", ph: "ec_leverage", required: true },
          { key: "argsJson", label: "参数 JSON（整值写 ${x} 保留原类型）", kind: "textarea",
            ph: '{"codes": "${params.codes}", "asof": "${params.asof}"}' },
        ] },
      { type: "code", label: "代码块", icon: "code", desc: "直接贴代码执行（临时场景）",
        fields: [
          { key: "lang", label: "语言", kind: "select", opts: ["python", "node", "shell"] },
          { key: "code", label: "代码（支持 ${}）", kind: "textarea", ph: "print('hello ${inputs.x}')" },
          { key: "timeout", label: "超时（秒，0=默认 600）", kind: "number", ph: "600" },
        ] },
    ],
  },
  {
    group: "网络",
    items: [
      { type: "tool", label: "网络搜索", icon: "globe", preset: { tool: "web" }, desc: "搜索引擎查询",
        fields: [{ key: "argsJson", label: "参数 JSON", kind: "textarea", ph: '{"action": "search", "query": "...", "limit": 5}' }, { key: "tool", label: "工具名", kind: "text" }] },
      { type: "tool", label: "抓取网页", icon: "globe", preset: { tool: "web" }, desc: "URL 转文本",
        fields: [{ key: "argsJson", label: "参数 JSON", kind: "textarea", ph: '{"action": "fetch", "url": "https://...", "render": false}' }, { key: "tool", label: "工具名", kind: "text" }] },
    ],
  },
  {
    group: "逻辑",
    items: [
      { type: "condition", label: "条件分支", icon: "branch", desc: "按表达式走 true/false；llm 判断默认总结队列，可指定模型",
        fields: [{ key: "expr", label: "表达式（如 len(${s1}) > 100）", kind: "text" },
                 { key: "model", label: "模型（llm 判断用）", kind: "model", ph: "留空=总结队列" }] },
      { type: "workflow", label: "子工作流", icon: "workflow", desc: "调用另一个工作流（拆大图用）",
        fields: [
          { key: "name", label: "子工作流名称（支持 ${}）", kind: "text", ph: "单镜制作" },
          { key: "inputsJson", label: "输入（JSON 对象，留空则透传 inputs）", kind: "textarea", ph: '{"shot": "第1镜"}' },
          { key: "output", label: "取哪段输出（final / node:节点id）", kind: "text", ph: "final" },
        ] },
      { type: "human", label: "人工闸门", icon: "check", desc: "流程挂起等人拍板（不是 handoff）",
        fields: [
          { key: "title", label: "标题", kind: "text", ph: "确认分镜，开始生成 30 张图" },
          { key: "ask", label: "说明", kind: "textarea", ph: "下面是要展示的内容说明" },
          { key: "show", label: "展示内容（每行一个变量）", kind: "textarea", ph: "${s2}" },
          { key: "options", label: "按钮（每行一个；可写 按钮=目标节点id）", kind: "textarea", ph: "批准\n驳回" },
          { key: "true", label: "选第1项后去哪（不写则走 next）", kind: "text", ph: "w8" },
          { key: "false", label: "选其它项后去哪（不写则走 next）", kind: "text", ph: "w2" },
          { key: "next", label: "统一出口（true/false 都没写时生效）", kind: "text", ph: "w8" },
          { key: "timeout", label: "等待超时（秒，0=一直等）", kind: "number", ph: "0" },
          { key: "onTimeout", label: "超时处理", kind: "select", opts: ["fail", "approve", "reject"] },
        ] },
      { type: "join", label: "汇合", icon: "check", desc: "多分支汇合点：同一趟只跑一次（带 condition/human 的图里扇出必须汇合到它）",
        fields: [
          { key: "next", label: "汇合后去哪", kind: "text", ph: "下游节点 id" },
        ] },
      { type: "loop", label: "循环", icon: "loop", desc: "body 子链重复 N 次，${__i__} 为轮次",
        fields: [
          { key: "times", label: "次数（支持 ${}）", kind: "text", ph: "3" },
          { key: "body", label: "循环体起始节点 id", kind: "text", ph: "b1" },
        ] },
      { type: "map", label: "Map 遍历", icon: "map", desc: "items 逐项跑 body，可配并发",
        fields: [
          { key: "items", label: "列表（逗号/换行分隔，支持 ${}）", kind: "textarea", ph: "a, b, c 或 ${s1}" },
          { key: "body", label: "循环体起始节点 id", kind: "text", ph: "b1" },
          { key: "collect", label: "收集哪个变量（默认 __item__=当前项）", kind: "text", ph: "body 里最后那个节点的 id" },
          { key: "concurrency", label: "并发数（0=跟随全局；受运行参数 parallel 约束）", kind: "number", ph: "3" },
          { key: "output", label: "输出形态（json 时 ${m1.results} 是数组，可下钻取字段）", kind: "select", opts: ["text", "json"] },
        ] },
    ],
  },
  {
    group: "扩展",
    items: [
      { type: "ocr", label: "OCR 识别", icon: "search", desc: "图片 → 文本（kind=ocr 模型）",
        fields: [
          { key: "path", label: "图片路径（${}）", kind: "text", ph: "${inputs.img}" },
          { key: "prompt", label: "识别提示词", kind: "text", ph: "识别图片中的所有文字" },
          { key: "model", label: "模型 spec（可选）", kind: "model", ph: "providerId/modelId" },
        ] },
      { type: "image", label: "生图", icon: "image", desc: "文本 → 图片（kind=image 模型）",
        fields: [
          { key: "prompt", label: "画面描述（${}）", kind: "textarea", ph: "一只在月球上的猫" },
          { key: "size", label: "尺寸", kind: "text", ph: "1024x1024" },
          { key: "model", label: "模型 spec（可选）", kind: "model", ph: "providerId/modelId" },
        ] },
      { type: "asr", label: "语音识别", icon: "mic", desc: "音频 → 文本（kind=asr 模型）",
        fields: [
          { key: "path", label: "音频路径（${}）", kind: "text", ph: "${inputs.audio}" },
          { key: "model", label: "模型 spec（可选）", kind: "model", ph: "providerId/modelId" },
        ] },
      { type: "mcp", label: "MCP 工具", icon: "plug", desc: "调用已连接的 MCP 工具",
        fields: [
          { key: "tool", label: "工具名（mcp__服务器__工具）", kind: "text" },
          { key: "argsJson", label: "参数 JSON（值支持 ${}）", kind: "textarea", ph: '{"key": "${s1}"}' },
        ] },
      { type: "tool", label: "内置函数", icon: "wrench", desc: "任意内置工具：文件/搜索/命令/skill 全部可用",
        fields: TOOL_FIELD },
      { type: "tool", label: "Skill", icon: "sparkle",
        preset: { tool: "tool", argsJson: '{"action": "use", "name": "skill__"}' },
        desc: "加载 skill 指南给后续节点用（skill 已并入 tool，走 action=use）",
        fields: [{ key: "argsJson", label: "参数 JSON", kind: "textarea", ph: '{"action": "use", "name": "skill__example"}' }, { key: "tool", label: "工具名", kind: "text" }] },
    ],
  },
];
export const ALL_ITEMS: PaletteItem[] = PALETTE.flatMap((g) =>
  g.items.map((it) => ({ ...it, group: g.group })),
);


const ICON_BY_TYPE: Record<string, string> = {
  llm: "robot", subagent: "puzzle", handoff: "export", write: "file-text", read_file: "book",
  exec: "bolt", code: "code", web_search: "globe", web_fetch: "globe", condition: "branch",
  loop: "loop", map: "map", human: "check", join: "check", workflow: "workflow",
  ocr: "search", image: "image", asr: "mic", mcp: "plug", tool: "wrench",
};
const ICON_BY_GROUP: Record<string, string> = {
  LLM: "robot", "文件 IO": "folder-open", 代码: "code", 网络: "globe", 逻辑: "branch", 扩展: "plug",
};
const TITLE_BY_GROUP: Record<string, string> = {
  LLM: "LLM", "文件 IO": "文件 IO", 代码: "代码",
  网络: "网络", 逻辑: "逻辑", 扩展: "扩展",
};
const GROUP_ORDER = ["LLM", "文件 IO", "代码", "网络", "逻辑", "扩展"];
const FIELD_KINDS = ["text", "textarea", "code", "select", "number", "boolean", "model"] as const;

function fieldKind(k: string): PaletteField["kind"] {
  return FIELD_KINDS.includes(k as (typeof FIELD_KINDS)[number])
    ? (k as PaletteField["kind"])
    : "text";
}


export function catalogToItems(catalog: NodeCatalogItem[] | null | undefined): PaletteItem[] {
  if (!catalog || catalog.length === 0) return ALL_ITEMS;
  return catalog.map((c) => ({
    type: c.type,
    label: c.label,
    desc: c.desc,
    icon: ICON_BY_TYPE[c.type] ?? ALL_ITEMS.find((i) => i.type === c.type)?.icon
      ?? ICON_BY_GROUP[c.group] ?? "puzzle",
    group: c.group || "其它",
    fields: (c.fields ?? []).map((f) => ({
      key: f.key,
      label: f.label,
      kind: fieldKind(f.kind),
      ph: f.placeholder || undefined,
      opts: f.options?.length ? f.options : undefined,
      required: f.required,
    })),
  }));
}

function groupItems(items: PaletteItem[]) {
  const groups = new Map<string, PaletteItem[]>();
  for (const it of items) {
    const g = it.group ?? "其它";
    const arr = groups.get(g);
    if (arr) arr.push(it);
    else groups.set(g, [it]);
  }
  const rank = (g: string) => {
    const i = GROUP_ORDER.indexOf(g);
    return i < 0 ? GROUP_ORDER.length : i;
  };
  return [...groups.entries()]
    .sort((a, b) => rank(a[0]) - rank(b[0]))
    .map(([group, groupItems]) => ({
      group, title: TITLE_BY_GROUP[group] ?? group, items: groupItems,
    }));
}

export const CODE_TEMPLATE = `# 代码节点协议：
# - 变量替换：\${inputs.x}（运行输入）、\${节点id}（上游节点输出）在执行前文本替换
# - 输出：stdout 即本节点输出，下游节点用 \${本节点id} 引用
# - lang: python / node / shell，代码写入临时文件执行
# 示例：读取输入并处理
import json, sys

text = "\${inputs.input}"
print(json.dumps({"len": len(text), "text": text}, ensure_ascii=False))
`;

export type { PaletteItem };

interface Props {
  items: PaletteItem[];
  onAdd: (item: PaletteItem, extra?: Record<string, unknown>) => void;
  onCreateCode: () => void;
  
  onClose?: () => void;
}

export function Palette({ items, onAdd, onCreateCode, onClose }: Props) {
  return (
    <div className="wf-palette">
      {onClose && <PanelClose onClose={onClose} title="收起节点列表" />}
      <button className="palette-item" title="创建代码节点并进入代码编辑" onClick={onCreateCode}>
        <Icon name="plus" />
        <div>
          <div className="palette-label">创建代码节点</div>
          <div className="dim">Python/TS 内联代码，进入代码编辑</div>
        </div>
      </button>
      {groupItems(items).map((g) => (
        <div key={g.group} className="palette-group">
          <div className="palette-title"><Icon name={nodeIcon(g.group)} /> {g.title}</div>
          {g.items.map((it) => (
            <div key={`${it.type}-${it.label}`} className="palette-item" title={it.desc}
              onClick={() => onAdd(it)}>
              <Icon name={it.icon as IconName} />
              <div>
                <div className="palette-label">{it.label}</div>
                <div className="dim">{it.desc}</div>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
