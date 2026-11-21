
import type { FlowNode } from "./parser";


export function findBackEdges(
  nodes: FlowNode[],
  edges: { from: string; to: string }[],
): Set<string> {
  const adj = new Map<string, string[]>();
  for (const n of nodes) adj.set(n.id, []);
  for (const e of edges) adj.get(e.from)?.push(e.to);
  const state = new Map<string, 0 | 1 | 2>(); 
  const back = new Set<string>();
  const key = (e: { from: string; to: string }) => `${e.from}\u0000${e.to}`;
  const dfs = (u: string) => {
    state.set(u, 1);
    for (const v of adj.get(u) ?? []) {
      const st = state.get(v) ?? 0;
      if (st === 1) back.add(key({ from: u, to: v }));
      else if (st === 0) dfs(v);
    }
    state.set(u, 2);
  };
  for (const n of nodes) if ((state.get(n.id) ?? 0) === 0) dfs(n.id);
  return back;
}


export function assignRanks(
  nodes: FlowNode[],
  edges: { from: string; to: string }[],
): Map<string, number> {
  const back = findBackEdges(nodes, edges);
  const fwd = edges.filter((e) => !back.has(`${e.from}\u0000${e.to}`) && e.from !== e.to);
  const indeg = new Map<string, number>();
  const out = new Map<string, string[]>();
  for (const n of nodes) {
    indeg.set(n.id, 0);
    out.set(n.id, []);
  }
  for (const e of fwd) {
    indeg.set(e.to, (indeg.get(e.to) ?? 0) + 1);
    out.get(e.from)?.push(e.to);
  }
  const rank = new Map<string, number>();
  for (const n of nodes) rank.set(n.id, 0);
  
  const queue = nodes.filter((n) => (indeg.get(n.id) ?? 0) === 0).map((n) => n.id);
  const seen = new Set<string>();
  while (queue.length) {
    const u = queue.shift()!;
    seen.add(u);
    for (const v of out.get(u) ?? []) {
      rank.set(v, Math.max(rank.get(v) ?? 0, (rank.get(u) ?? 0) + 1));
      indeg.set(v, (indeg.get(v) ?? 0) - 1);
      if ((indeg.get(v) ?? 0) === 0) queue.push(v);
    }
  }
  
  for (const n of nodes) if (!seen.has(n.id)) rank.set(n.id, rank.get(n.id) ?? 0);
  return rank;
}


export function orderWithinRanks(
  layers: string[][],
  preds: Map<string, string[]>,
  succs: Map<string, string[]>,
  iter = 4,
): void {
  const indexOf = (layer: string[]) => {
    const m = new Map<string, number>();
    layer.forEach((id, i) => m.set(id, i));
    return m;
  };
  for (let it = 0; it < iter; it++) {
    const down = it % 2 === 0;
    const order = down ? layers.map((_, i) => i) : layers.map((_, i) => layers.length - 1 - i);
    for (const li of order) {
      const layer = layers[li];
      const refLayer = down ? layers[li - 1] : layers[li + 1];
      if (!refLayer) continue;
      const refIdx = indexOf(refLayer);
      const relation = down ? preds : succs;
      const score = new Map<string, number>();
      layer.forEach((id, i) => {
        const keys = (relation.get(id) ?? []).filter((p) => refIdx.has(p));
        const v = keys.length
          ? keys.reduce((s, p) => s + (refIdx.get(p) ?? 0), 0) / keys.length
          : i; 
        score.set(id, v);
      });
      layer.sort((a, b) => (score.get(a)! - score.get(b)!) || (layer.indexOf(a) - layer.indexOf(b)));
    }
  }
}
