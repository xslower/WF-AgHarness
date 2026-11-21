
import type { AppConfig, ModelInfo } from "../api";
import { nowHM } from "../ui/format";


export function splitSpec(spec: string): [string, string] {
  const i = spec.indexOf("/");
  return i < 0 ? [spec, ""] : [spec.slice(0, i), spec.slice(i + 1)];
}

export function modelOf(config: AppConfig | null, spec: string): ModelInfo | undefined {
  if (!config || !spec || !spec.includes("/")) return undefined;
  const [pname, mid] = splitSpec(spec);
  return config.providers.find((x) => x.name === pname)?.models.find((m) => m.id === mid);
}

export function specLabel(config: AppConfig | null, spec: string): string {
  if (!config) return spec;
  const [pname, mid] = splitSpec(spec);
  const p = config.providers.find((x) => x.name === pname);
  return p ? `${p.name} · ${mid}` : spec;
}


export function isInSchedule(config: AppConfig | null, spec: string): boolean {
  const scheds = modelOf(config, spec)?.schedules;
  if (!scheds?.length) return true;
  const now = nowHM();
  const wd = (new Date().getDay() + 6) % 7; 
  return scheds.some((s) => {
    const dayOk = !s.days?.length || s.days.includes(wd);
    const st = s.start || "00:00";
    const en = s.end || "23:59";
    const timeOk = st <= en ? now >= st && now <= en : now >= st || now <= en;
    return dayOk && timeOk;
  });
}


export function allModelSpecs(config: AppConfig | null): string[] {
  if (!config) return [];
  return config.providers
    .flatMap((p) =>
      p.models
        .filter((m) => (m.kind === "lm" || m.kind === "") && !m.disabled)
        .map((m) => `${p.name}/${m.id}`))
    .filter((s) => isInSchedule(config, s));
}


export interface ModelOption {
  value: string;   
  label: string;
}


export const QUEUE_NAMES = ["parent", "child", "summary"] as const;
export type QueueName = typeof QUEUE_NAMES[number];


export const QUEUE_LABELS: Record<QueueName, string> = {
  parent: "父队列",
  child: "子队列",
  summary: "总结队列",
};


export const DEFAULT_SPEC: QueueName = "parent";   


export const WF_NODE_DEFAULT_SPEC: QueueName = "summary";


export function normalizeNodeModel(raw: string | null | undefined): string {
  const s = (raw ?? "").trim();
  return s || WF_NODE_DEFAULT_SPEC;
}

export function normalizeSpec(raw: string | null | undefined): string {
  const s = (raw ?? "").trim();
  return s || DEFAULT_SPEC;
}


export function isQueueSpec(raw: string): boolean {
  return (QUEUE_NAMES as readonly string[]).includes(raw);
}


export function modelOptions(config: AppConfig | null): ModelOption[] {
  const opts: ModelOption[] = [
    { value: DEFAULT_SPEC, label: QUEUE_LABELS.parent }];
  if ((config?.queues?.child?.length ?? 0) > 0) {
    opts.push({ value: "child", label: QUEUE_LABELS.child });
  }
  if ((config?.queues?.summary?.length ?? 0) > 0) {
    opts.push({ value: "summary", label: QUEUE_LABELS.summary });
  }
  for (const s of allModelSpecs(config)) {
    opts.push({ value: s, label: config ? specLabel(config, s) : s });
  }
  return opts;
}

export interface ContextStats {
  activeSpec: string;
  limit: number;
  used: number;
  pct: number;
  warnRatio: number;
  
  estimated: boolean;
}

export function contextStats(
  config: AppConfig | null,
  modelSel: string,
  ctxState: { used: number; model: string; estimated?: boolean } | null,
): ContextStats {
  
  
  
  const activeSpec = isQueueSpec(modelSel)
    ? (ctxState?.model || config?.queues.parent[0] || "")
    : modelSel;
  const limit = modelOf(config, activeSpec)?.contextLength ?? 1_000_000;
  const used = ctxState?.used ?? 0;
  return {
    activeSpec,
    limit,
    used,
    pct: Math.min(100, (used / limit) * 100),
    warnRatio: config?.settings.contextWarnRatio ?? 0.6,
    
    estimated: ctxState?.estimated === true,
  };
}
