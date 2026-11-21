
import type { Connection, Edge } from "@xyflow/react";
import type { PaletteItem } from "./Palette";
import { CODE_TEMPLATE } from "./Palette";
import { WF_NODE_DEFAULT_SPEC } from "../../kernel/model/modelSpec";


export const NODE_DEFAULTS: Record<string, Record<string, string>> = {
  llm: { prompt: "处理：${inputs.input}", model: WF_NODE_DEFAULT_SPEC },
  write: { path: "out/output.md", content: "${prev}" },
  exec: { command: "echo hello" },
  condition: { expr: "len(${prev}) > 0", model: WF_NODE_DEFAULT_SPEC },
  human: { title: "确认继续吗？", options: "批准\n驳回" },
  workflow: { name: "子工作流", output: "final" },
  web_search: { query: "${inputs.input}" },
  web_fetch: { url: "https://example.com" },
  read_file: { path: "README.md" },
  subagent: { task: "完成以下任务：${inputs.input}", model: WF_NODE_DEFAULT_SPEC },
  code: { code: CODE_TEMPLATE, lang: "python" },
};


export function nodeId(type: string, counter: number): string {
  return `${type === "tool" ? "f" : type[0]}${counter}`;
}


export function canAddNode(orchestration: boolean, type: string): boolean {
  return !orchestration || type === "llm";
}


export function buildNodeDsl(
  item: PaletteItem,
  id: string,
  extra?: Record<string, unknown>,
  defaults: Record<string, Record<string, string>> = NODE_DEFAULTS,
): Record<string, unknown> {
  const dsl: Record<string, unknown> = {
    id, type: item.type, ...(item.preset ?? {}), ...(extra ?? {}),
  };
  for (const f of item.fields) {
    if (dsl[f.key] === undefined) dsl[f.key] = f.kind === "select" ? (f.opts?.[0] ?? "") : "";
  }
  const defs = defaults[item.type];
  if (defs) for (const [k, v] of Object.entries(defs)) if (!dsl[k]) dsl[k] = v;
  if ((item.type === "mcp" || item.type === "tool") && dsl.argsJson === "") dsl.argsJson = "{}";
  return dsl;
}


export function placeNewNode(count: number): { x: number; y: number } {
  return { x: 100 + (count % 3) * 320, y: 90 + Math.floor(count / 3) * 170 };
}


export function connectEdges(edges: Edge[], c: Connection): Edge[] {
  if (!c.source || !c.target || c.source === c.target) return edges;
  const dup = edges.some((e) => e.source === c.source && e.target === c.target
    && (e.sourceHandle ?? null) === (c.sourceHandle ?? null));
  if (dup) return edges;
  const base = c.sourceHandle === "true" || c.sourceHandle === "false"
    ? edges.filter((e) => !(e.source === c.source && e.sourceHandle === c.sourceHandle))
    : edges;
  return [...base, {
    ...c,
    id: `${c.source}-${c.sourceHandle ?? "out"}-${c.target}`,
  } as Edge];
}


export function removeNode(edges: Edge[], id: string): Edge[] {
  return edges.filter((e) => e.source !== id && e.target !== id);
}


export function extractChain(
  nodes: { id: string; data?: unknown }[],
  edges: Edge[],
  startId: string,
): string[] {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const ids: string[] = [];
  const seen = new Set<string>();
  let cur: string | undefined = startId;
  while (cur && byId.has(cur) && !seen.has(cur)) {
    const dsl = ((byId.get(cur)!.data as { dsl?: Record<string, unknown> })?.dsl) ?? {};
    const type = String(dsl.type || "");
    
    if (ids.length > 0 && (type === "condition" || type === "human"
        || type === "loop" || type === "map")) {
      
      break;
    }
    ids.push(cur);
    seen.add(cur);
    const outs = edges.filter((e) => e.source === cur);
    if (outs.length !== 1) break;                 
    const next: string = outs[0].target;
    const incoming = edges.filter((e) => e.target === next);
    if (incoming.length !== 1) break;             
    if (seen.has(next)) break;                    
    cur = next;
  }
  return ids;
}
