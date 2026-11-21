
import { createContext, useContext } from "react";
import type { Edge, Node } from "@xyflow/react";
import type { WorkflowDef } from "../../kernel/api";
import { ALL_ITEMS, type PaletteItem } from "./Palette";

export interface FlowNodeData extends Record<string, unknown> {
  dsl: Record<string, unknown>;
  status?: string;
  [key: string]: unknown;
}


export const PaletteItemsContext = createContext<PaletteItem[]>(ALL_ITEMS);

export const itemOf = (t: string, items: PaletteItem[] = ALL_ITEMS): PaletteItem =>
  items.find((i) => i.type === t)
  ?? ALL_ITEMS.find((i) => i.type === t)
  ?? { type: t, label: t, desc: "", icon: "🧩", group: "其它", fields: [] };

export const usePaletteItem = (t: string): PaletteItem =>
  itemOf(t, useContext(PaletteItemsContext));

const edgeKey = (source: string, handle: string | null | undefined, target: string) =>
  `${source}-${handle ?? "out"}-${target}`;


function edgesFromNodes(wf: WorkflowDef): Edge[] {
  const out: Edge[] = [];
  for (const n of wf.nodes) {
    if (n.type === "condition" || n.type === "human") {
      if (n.true) out.push({ id: edgeKey(n.id, "true", n.true), source: n.id, target: String(n.true), sourceHandle: "true", label: n.type === "human" ? "批准" : "true" });
      if (n.false) out.push({ id: edgeKey(n.id, "false", n.false), source: n.id, target: String(n.false), sourceHandle: "false", label: n.type === "human" ? "驳回" : "false" });
    } else if (n.type === "loop" || n.type === "map") {
      if (n.body) out.push({ id: edgeKey(n.id, "body", String(n.body)), source: n.id, target: String(n.body),
        sourceHandle: "body", label: "body", style: { strokeDasharray: "6 3" } });
      if (n.next) out.push({ id: edgeKey(n.id, "out", String(n.next)), source: n.id, target: String(n.next) });
    } else if (n.next) {
      out.push({ id: edgeKey(n.id, "out", String(n.next)), source: n.id, target: String(n.next) });
    }
  }
  return out;
}

export function dslToCanvas(wf: WorkflowDef): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const sourceEdges = wf.edges?.length ? wf.edges : edgesFromNodes(wf);
  const canvasEdges: Edge[] = sourceEdges.map((e) => ({
    id: edgeKey(e.source, e.sourceHandle, e.target),
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle && e.sourceHandle !== "out"
      ? e.sourceHandle : undefined,
    targetHandle: e.targetHandle ?? undefined,
    label: e.sourceHandle === "true" || e.sourceHandle === "false"
      ? e.sourceHandle
      : e.sourceHandle === "body" ? "body" : undefined,
    animated: e.sourceHandle === "true",
    style: e.sourceHandle === "body" ? { strokeDasharray: "6 3" } : undefined,
  }));
  
  const byId = new Map(wf.nodes.map((n) => [n.id, n]));
  const adj = new Map<string, string[]>();
  for (const e of sourceEdges) {
    const arr = adj.get(e.source) ?? [];
    arr.push(e.target);
    adj.set(e.source, arr);
  }
  const depth = new Map<string, number>();
  const queue: [string, number][] = wf.nodes[0] ? [[wf.nodes[0].id, 0]] : [];
  while (queue.length) {
    const [id, d] = queue.shift()!;
    if (depth.has(id) || !byId.has(id)) continue;
    depth.set(id, d);
    for (const next of adj.get(id) ?? []) queue.push([next, d + 1]);
  }
  const perDepth = new Map<number, number>();
  wf.nodes.forEach((n, i) => {
    
    const saved = typeof n.pos === "string"
      ? String(n.pos).split(",").map(Number) : null;
    const hasPos = saved && saved.length === 2 && saved.every((v) => Number.isFinite(v));
    const d = depth.get(n.id) ?? Math.max(i, 0);
    const k = perDepth.get(d) ?? 0;
    perDepth.set(d, k + 1);
    nodes.push({
      id: n.id, type: "dsl",
      position: hasPos ? { x: saved[0], y: saved[1] } : { x: 120 + k * 300 + d * 40, y: 40 + d * 150 },
      data: { dsl: { ...n } } as FlowNodeData,
    });
  });
  return { nodes, edges: canvasEdges };
}

export function canvasToDsl(wf: WorkflowDef, nodes: Node[], edges: Edge[]): WorkflowDef {
  const savedEdges = edges.map((e) => ({
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle || "out",
    targetHandle: e.targetHandle ?? undefined,
  }));
  const out: WorkflowDef["nodes"] = nodes.map((n) => {
    const d = (n.data as FlowNodeData).dsl as Record<string, unknown>;
    const nd: Record<string, unknown> = { ...d, id: n.id };
    delete nd.next; delete nd.true_; delete nd.false_;
    
    nd.pos = `${Math.round(n.position.x)},${Math.round(n.position.y)}`;
    if (d.type === "condition" || d.type === "human") {
      nd.true = edges.find((e) => e.source === n.id && e.sourceHandle === "true")?.target ?? "";
      nd.false = edges.find((e) => e.source === n.id && e.sourceHandle === "false")?.target ?? "";
    } else if (d.type === "loop" || d.type === "map") {
      const body = edges.find((e) => e.source === n.id && e.sourceHandle === "body")?.target;
      if (body) nd.body = body;
      const nx = edges.find((e) => e.source === n.id && (!e.sourceHandle || e.sourceHandle === "out"))?.target;
      if (nx) nd.next = nx;
    } else {
      const nx = edges.find((e) => e.source === n.id && (!e.sourceHandle || e.sourceHandle === "out"))?.target;
      if (nx) nd.next = nx;
    }
    return nd as unknown as WorkflowDef["nodes"][number];
  });
  return { ...wf, edges: savedEdges, nodes: out };
}
