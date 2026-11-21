
import type { Settings } from "../../kernel/api";

export type SettingKind = "text" | "number" | "select" | "lines" | "boolean";

export interface SettingDef {
  key: keyof Settings;
  label: string;
  kind: SettingKind;
  help?: string;
  placeholder?: string;
  options?: { value: string; label: string }[];
  min?: number;
}

export interface SettingGroup {
  title: string;
  fields: SettingDef[];
}

export const SETTING_GROUPS: SettingGroup[] = [
  {
    title: "路径",
    fields: [
      { key: "workspaceRoot", label: "工作目录", kind: "text",
        help: "Agent 操作的根目录" },
      { key: "projectsRoot", label: "项目根目录", kind: "text",
        placeholder: "留空 = 默认", help: "多项目树，默认 <仓库>/projects" },
      { key: "runtimeDir", label: "运行时数据目录", kind: "text",
        placeholder: "如 ~/usb1/agent",
        help: "会话库/事件库/草稿/运行记录；留空 = 留在项目内 .agent/。共享盘（NTFS/网络盘）每次小文件读写都要用户态往返，是「点什么都慢半拍」的常见原因。改完需重启后端；已有数据用 python -m app.migrate_runtime_dir --commit 迁移，未迁移时仍读旧位置（不会丢会话）。" },
    ],
  },
  {
    title: "指令模板",
    fields: [
      { key: "promptTemplateMode", label: "启用方式", kind: "select",
        help: "前缀{指令}后缀，长上下文反复强调规定用",
        options: [
          { value: "off", label: "不启用" },
          { value: "once", label: "仅会话首条生效" },
          { value: "every", label: "每条指令都带上" },
        ] },
      { key: "promptPrefix", label: "前缀", kind: "text",
        placeholder: "如：你是XX项目的助手，严格遵守：" },
      { key: "promptSuffix", label: "后缀", kind: "text", placeholder: "后缀" },
    ],
  },
  {
    title: "执行与压缩",
    fields: [
      { key: "escalateFileLimit", label: "改动文件数提示阈值", kind: "number", min: 0,
        help: "一轮对话里改动多少个不同文件后，才提示先出计划；0 = 不按文件数提示" },
      { key: "maxToolRounds", label: "单轮工具调用轮数上限", kind: "number", min: 0,
        help: "模型一轮里最多连续调多少次工具；长任务可调大，0 = 用 profile 默认值" },
      { key: "compactSummaryMode", label: "上下文压缩形态", kind: "select",
        help: "batch=助手回复合并成一段总结；per_message=旧的逐条一两句",
        options: [
          { value: "batch", label: "batch（合并成一段，推荐）" },
          { value: "per_message", label: "per_message（逐条总结）" },
        ] },
      { key: "compactUserMsgLimit", label: "用户消息压缩阈值", kind: "number", min: 0,
        help: "超过该字数才首尾折叠，原文仍可用 memory(history_get) 取回；0 = 永不压缩用户消息" },
      { key: "summaryHedgeMs", label: "总结调用对冲（毫秒）", kind: "number", min: 0,
        help: "主模型超过该毫秒数未完成就并发拉起队列里其余模型抢答；0 = 关闭" },
      { key: "defaultEffort", label: "默认思考强度", kind: "select",
        options: ["off", "low", "medium", "high"].map((v) => ({ value: v, label: v })) },
    ],
  },
  {
    title: "安全与清理",
    fields: [
      { key: "policyExtraSafePaths", label: "额外放行目录", kind: "lines",
        placeholder: "每行一个，如 ~/scratch",
        help: "每行一个；写这些目录不算「出项目」、不弹审批。临时目录（/tmp、/var/tmp、%TEMP%、$TMPDIR）已自动放行；系统关键路径（/etc、~/.ssh 等）仍然拦截。" },
      { key: "trashEnabled", label: "删除先进回收站", kind: "boolean",
        help: "项目内 .trash 可手工恢复；关闭 = 项目内直接真删，项目外始终禁止" },
      { key: "trashRetentionDays", label: "回收站保留天数", kind: "number", min: 0,
        help: "超过即自动清理；0 = 不自动清，只手动清" },
      { key: "wfChatRetentionDays", label: "画布会话保留天数", kind: "number", min: 0,
        help: "工作流/编排画布会话不进项目任务列表，用画布右侧「历史」浮窗查看；0 = 不自动清" },
    ],
  },
  {
    title: "交互",
    fields: [
      { key: "quickSuggestions", label: "回复后生成快捷指令", kind: "boolean",
        help: "自动生成快捷指令建议（需先在「模型队列」为「快捷建议」选模型；留空=禁用）" },
      { key: "notifyOnSessionDone", label: "后台会话完成通知", kind: "boolean",
        help: "多会话：你正在看别的会话时，后台会话跑完一轮会弹一条系统通知（需要浏览器授权）" },
    ],
  },
];


export function inlineKind(def: SettingDef): "text" | "number" | "select" | "lines" {
  return def.kind === "boolean" ? "text" : def.kind;
}


export function parseSetting(def: SettingDef, raw: string): Settings[keyof Settings] {
  if (def.kind === "number") return Number(raw) || 0;
  if (def.kind === "boolean") return raw === "true";
  if (def.kind === "lines") return raw.split("\n").map((s) => s.trim()).filter(Boolean);
  return raw;
}


export function formatSetting(def: SettingDef, v: Settings[keyof Settings]): string {
  if (def.kind === "lines") return Array.isArray(v) ? v.join("\n") : "";
  if (def.kind === "boolean") return v === true ? "true" : "false";
  return v == null ? "" : String(v);
}
