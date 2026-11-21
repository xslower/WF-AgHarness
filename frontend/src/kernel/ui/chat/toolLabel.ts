
import { baseName } from "../format";

export interface ToolLabel {
  
  title: string;
  
  detail: string;
}


const TITLES: Record<string, string> = {
  f_read: "读取文件",
  f_write: "写文件",
  f_replace: "改文件",
  config_write: "写数据文件",
  search_files: "搜索文件",
  grep: "搜索内容",
  f_path: "文件操作",
  run_command: "执行命令",
  web: "联网",
  gen_image: "生成图片",
  asr: "语音转写",
  ocr: "图片识别",
  screenshot: "截屏",
  system_info: "系统信息",
  table: "读取表格",
  ppt: "演示稿",
  subagent: "子任务",
  memory: "记忆",
  workflow: "工作流",
  tool: "工具检索",
  todo: "待办",
  trash: "回收站",
};


const F_PATH_ACTIONS: Record<string, string> = {
  list: "列目录",
  view: "查看路径",
  mkdir: "新建目录",
  move: "移动",
  copy: "复制",
  delete: "删除",
  write: "写入文件",
  info: "查看文件信息",
  exists: "检查路径",
};


const CMD_WHITELIST = new Set([
  "git", "npm", "pnpm", "yarn", "npx", "python", "python3", "node", "deno", "bun",
  "pip", "pytest", "uvicorn", "make", "docker", "docker-compose", "cargo", "go",
  "ls", "cat", "head", "tail", "wc", "grep", "rg", "find", "tree", "du", "df", "ps",
  "ss", "curl", "wget", "ffmpeg", "ffprobe", "tar", "zip", "unzip", "mkdir", "cp",
  "mv", "rm", "touch", "chmod", "sed", "awk", "sort", "uniq", "xargs", "jq",
]);

function clip(s: string, max = 48): string {
  const t = String(s || "").replace(/\s+/g, " ").trim();
  return t.length > max ? `${t.slice(0, max)}…` : t;
}


function stripAux(tokens: string[]): string[] {
  let t = tokens.slice();
  for (;;) {
    const h = t[0];
    if (!h) return t;
    if (h === "timeout") { t = t.slice(2); continue; }        
    if (h === "env") {                                        
      t = t.slice(1);
      while (t.length && t[0].includes("=")) t = t.slice(1);
      continue;
    }
    if (h.includes("=") && !h.startsWith("-")) { t = t.slice(1); continue; }  
    return t;
  }
}


export function coreCommand(command: string): string {
  const raw = String(command || "").trim();
  if (!raw) return "";
  
  const parts = raw.split(/&&|\|\||;|\n/).map((x) => x.trim()).filter(Boolean);
  for (const part of parts) {
    const tokens = stripAux(part.split(/\s+/).filter(Boolean));
    const head = tokens[0] || "";
    if (!head) continue;
    
    if (head === "cd" || head === "export" || head === "set") continue;
    const base = baseName(head);
    if (!CMD_WHITELIST.has(base)) return "";   
    return clip(tokens.slice(0, 3).join(" "), 60);
  }
  return "";
}

function pick(args: Record<string, unknown>, ...keys: string[]): string {
  for (const k of keys) {
    const v = args[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}


function pickNum(args: Record<string, unknown>, ...keys: string[]): string {
  for (const k of keys) {
    const v = args[k];
    if (typeof v === "number" && Number.isFinite(v)) return String(v);
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}


const SIMPLE_DETAIL: Record<string, [string[], number]> = {
  
  f_read: [["file_path", "path", "picture"], 40],
  table: [["file_path", "path", "picture"], 40],
  ppt: [["file_path", "path", "picture"], 40],
  asr: [["file_path", "path", "picture"], 40],
  ocr: [["file_path", "path", "picture"], 40],
  gen_image: [["prompt"], 40],
  workflow: [["name", "topic"], 32],
  tool: [["query", "name"], 32],
  subagent: [["task", "message"], 40],
};


const COMPOSITE_DETAIL: Record<string, (a: Record<string, unknown>) => string> = {
  run_command: (a) => coreCommand(pick(a, "command")),
  
  grep: (a) => {
    const k = a.key;
    return clip(Array.isArray(k) ? k.join(" / ") : pick(a, "key"), 40);
  },

  f_write: writeDetail,
  f_replace: writeDetail,
  config_write: configDetail,
  search_files: (a) => {
    const pat = pick(a, "pattern");
    const dir = pick(a, "path");
    
    const showDir = !!dir && dir !== "." && dir !== "./";
    return clip([pat, showDir ? dir : ""].filter(Boolean).join(" · "), 48);
  },
  f_path: (a) => clip([pick(a, "path"), pick(a, "dest")].filter(Boolean).join(" → "), 56),
  web: (a) => clip(pick(a, "query") || pick(a, "url"), 48),
  
  memory: (a) => {
    const act = pick(a, "action");
    if (act === "history_get") {
      const ids = a.ids;
      return Array.isArray(ids) && ids.length ? `msg#${ids.join(",")}` : "历史消息";
    }
    if (act === "replace" || act === "delete") return clip(pick(a, "mid"), 32);
    return clip(pick(a, "query") || pick(a, "content"), 32);
  },
};


function writeDetail(a: Record<string, unknown>): string {
  const p = pick(a, "path");
  const before = pickNum(a, "before");
  const after = pickNum(a, "after");
  const replace = pick(a, "replace");
  const parts = [p ? clip(baseName(p), 40) : ""];
  if (replace) parts.push(`第 ${replace} 行`);
  else if (before) parts.push(`第 ${before} 行前`);
  else if (after) parts.push(`第 ${after} 行后`);
  else if (a.append) parts.push("末尾");
  return clip(parts.filter(Boolean).join(" · "), 56);
}


function configDetail(a: Record<string, unknown>): string {
  const p = pick(a, "path");
  const ops = a.ops;
  const n = Array.isArray(ops) ? ops.length : ops ? 1 : 0;
  return clip([p ? baseName(p) : "", n ? `${n} 处改动` : ""].filter(Boolean).join(" · "), 56);
}

function detailOf(name: string, args: Record<string, unknown>): string {
  const composite = COMPOSITE_DETAIL[name];
  if (composite) return composite(args);
  const simple = SIMPLE_DETAIL[name];
  if (!simple) return "";
  const [keys, max] = simple;
  
  return clip(baseName(pick(args, ...keys)), max);
}


function titleOf(name: string, args: Record<string, unknown>): string {
  const base = TITLES[name] || name;
  const action = typeof args.action === "string" ? args.action : "";
  if (name === "f_path" && action && F_PATH_ACTIONS[action]) return F_PATH_ACTIONS[action];
  if (name === "web") {
    if (action === "inspect") return "调试网页";
    if (action === "fetch") return "打开网页";
    if (action === "search") return "联网搜索";
    return args.query ? "联网搜索" : "打开网页";
  }
  if (name === "subagent" && action) return "子任务";
  if (name === "table" && action === "query") return "查询表格";
  if (name === "ppt" && action) return "编辑演示稿";
  if (name === "todo") return "待办清单";
  return base;
}


export function toolLabel(name: string, args?: unknown): ToolLabel {
  const raw = String(name || "").trim();
  const a = (args && typeof args === "object" ? args : {}) as Record<string, unknown>;
  
  if (raw.startsWith("mcp__")) {
    const body = raw.slice(5);
    const i = body.indexOf("__");
    if (i > 0) return { title: `${body.slice(0, i)}/${body.slice(i + 2)}`, detail: "" };
    return { title: raw, detail: "" };
  }
  const title = titleOf(raw, a);
  return { title, detail: detailOf(raw, a) };
}
