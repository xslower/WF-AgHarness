
import type { Edge, Node } from "@xyflow/react";
import { extractChain } from "./graphOps";

export interface SubflowDef {
  name: string;
  desc: string;
  inputs: { name: string; desc?: string; type?: string }[];
  nodes: Record<string, unknown>[];
  edges: { source: string; target: string; sourceHandle: string }[];
}

export interface ExtractResult {
  
  sub: SubflowDef;
  
  nodes: Node[];
  edges: Edge[];
  
  newNodeId: string;
  
  moved: string[];
}

const dslOf = (n: Node | undefined): Record<string, unknown> =>
  ((n?.data as { dsl?: Record<string, unknown> })?.dsl) ?? {};


const PREV = "${prev}";
const SUB_INPUT = "${inputs.input}";

function rewritePrev(value: unknown): unknown {
  if (typeof value === "string") return value.split(PREV).join(SUB_INPUT);
  if (Array.isArray(value)) return value.map(rewritePrev);
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = rewritePrev(v);
    }
    return out;
  }
  return value;
}


export function buildSubflow(
  nodes: Node[],
  edges: Edge[],
  startId: string,
  subName: string,
  newNodeId: string,
): ExtractResult | null {
  const chain = extractChain(nodes, edges, startId);
  if (chain.length === 0) return null;
  const chainSet = new Set(chain);
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const startNode = byId.get(startId);
  if (!startNode) return null;

  
  const subNodes = chain.map((id, i) => {
    const dsl = { ...dslOf(byId.get(id)) };
    dsl.id = id;
    
    delete dsl.pos;
    return (i === 0 ? (rewritePrev(dsl) as Record<string, unknown>) : dsl);
  });
  const subEdges = edges
    .filter((e) => chainSet.has(e.source) && chainSet.has(e.target))
    .map((e) => ({
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle || "out",
    }));

  
  const incoming = edges.filter((e) => e.target === startId && !chainSet.has(e.source));
  const lastId = chain[chain.length - 1];
  const outgoing = edges.filter((e) => e.source === lastId && !chainSet.has(e.target));
  const restNodes = nodes.filter((n) => !chainSet.has(n.id));
  const restEdges = edges.filter(
    (e) => !chainSet.has(e.source) && !chainSet.has(e.target));

  const wfNode: Node = {
    id: newNodeId,
    type: "dsl",
    position: { ...startNode.position },
    data: {
      dsl: {
        id: newNodeId,
        type: "workflow",
        name: subName,
        inputsJson: JSON.stringify({ input: PREV }),
        output: "final",
      },
    },
  };
  const bridgeEdges: Edge[] = [
    ...incoming.map((e) => ({
      ...e,
      id: `${e.source}-${e.sourceHandle ?? "out"}-${newNodeId}`,
      target: newNodeId,
    })),
    ...outgoing.map((e) => ({
      ...e,
      id: `${newNodeId}-${e.sourceHandle ?? "out"}-${e.target}`,
      source: newNodeId,
    })),
  ];

  return {
    sub: {
      name: subName,
      desc: `从「${subName}」抽出的子流程（${chain.join(" → ")}）`,
      inputs: [{ name: "input", desc: "上游内容（原 \u0024{prev}）", type: "string" }],
      nodes: subNodes,
      edges: subEdges,
    },
    nodes: [...restNodes, wfNode],
    edges: [...restEdges, ...bridgeEdges],
    newNodeId,
    moved: chain,
  };
}


export function uniqueName(base: string, taken: string[]): string {
  const set = new Set(taken);
  if (!set.has(base)) return base;
  for (let i = 2; i < 1000; i++) {
    const n = `${base}-${i}`;
    if (!set.has(n)) return n;
  }
  return `${base}-${Date.now()}`;
}
