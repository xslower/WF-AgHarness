
import type { FlowDirection, FlowGraph, NodeShape } from "./parser";
import { edgePath, pathBounds, routeAround, routeBack, selfLoopPath, shiftPath } from "./layoutEdge";
import { measureNode } from "./layoutMeasure";
import { assignRanks, orderWithinRanks } from "./layoutRank";

export { measureNode, wrapLabel, textWidth } from "./layoutMeasure";

export interface LaidNode {
  id: string;
  label: string;
  shape: NodeShape;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LaidEdge {
  from: string;
  to: string;
  label: string;
  style: "solid" | "dotted" | "thick";
  head: "arrow" | "circle" | "cross" | "none";
  tailHead: boolean;
  
  path: string;
  
  lx: number;
  ly: number;
  selfLoop: boolean;
}

export interface LaidGroup {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface FlowLayout {
  width: number;
  height: number;
  direction: FlowDirection;
  nodes: LaidNode[];
  edges: LaidEdge[];
  groups: LaidGroup[];
}


const RANK_GAP = 58;
const NODE_GAP = 34;

const GROUP_PAD = 16;

const GROUP_TITLE_H = 22;

export function layoutFlow(graph: FlowGraph): FlowLayout {
  const vertical = graph.direction !== "LR" && graph.direction !== "RL";
  const reversed = graph.direction === "BT" || graph.direction === "RL";

  const sizes = new Map<string, { w: number; h: number }>();
  for (const n of graph.nodes) sizes.set(n.id, measureNode(n.label, n.shape));

  const layers = buildLayers(graph);
  orderWithinRanks(layers, ...adjacency(graph));

  const nodes = placeNodes(graph, layers, sizes, vertical, reversed);
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const edges = routeEdges(graph, nodes, byId, vertical);
  const groups = layoutGroups(graph, byId);

  shiftPositive(nodes, edges, groups);
  return finish(graph, nodes, edges, groups);
}


function buildLayers(graph: FlowGraph): string[][] {
  const rank = assignRanks(graph.nodes, graph.edges);
  const usedRanks = [...new Set(rank.values())].sort((a, b) => a - b);
  const rankIndex = new Map(usedRanks.map((r, i) => [r, i]));
  const layers: string[][] = Array.from({ length: usedRanks.length }, () => []);
  for (const n of graph.nodes) layers[rankIndex.get(rank.get(n.id) ?? 0)!].push(n.id);
  return layers;
}


function adjacency(graph: FlowGraph): [Map<string, string[]>, Map<string, string[]>] {
  const preds = new Map<string, string[]>();
  const succs = new Map<string, string[]>();
  for (const n of graph.nodes) {
    preds.set(n.id, []);
    succs.set(n.id, []);
  }
  for (const e of graph.edges) {
    if (e.from === e.to) continue;
    preds.get(e.to)?.push(e.from);
    succs.get(e.from)?.push(e.to);
  }
  return [preds, succs];
}


function placeNodes(
  graph: FlowGraph,
  layers: string[][],
  sizes: Map<string, { w: number; h: number }>,
  vertical: boolean,
  reversed: boolean,
): LaidNode[] {
  const mainSize = (id: string) => (vertical ? sizes.get(id)!.h : sizes.get(id)!.w);
  const crossSize = (id: string) => (vertical ? sizes.get(id)!.w : sizes.get(id)!.h);

  const layerMain = layers.map((ids) => (ids.length ? Math.max(...ids.map(mainSize)) : 0));
  const layerMainStart: number[] = [];
  let acc = 0;
  for (let i = 0; i < layers.length; i++) {
    layerMainStart[i] = acc;
    acc += layerMain[i] + (i < layers.length - 1 ? RANK_GAP : 0);
  }
  const mainTotal = acc;

  const layerCross = layers.map((ids) => {
    if (!ids.length) return 0;
    return ids.reduce((s, id) => s + crossSize(id), 0) + (ids.length - 1) * NODE_GAP;
  });
  const crossTotal = Math.max(...layerCross, 0);

  const pos = new Map<string, { x: number; y: number; w: number; h: number }>();
  layers.forEach((ids, li) => {
    let c = (crossTotal - layerCross[li]) / 2;
    for (const id of ids) {
      const s = sizes.get(id)!;
      const mainPos = layerMainStart[li] + (layerMain[li] - mainSize(id)) / 2;
      if (vertical) pos.set(id, { x: c, y: mainPos, w: s.w, h: s.h });
      else pos.set(id, { x: mainPos, y: c, w: s.w, h: s.h });
      c += crossSize(id) + NODE_GAP;
    }
  });

  
  if (reversed) {
    for (const [, p] of pos) {
      if (vertical) p.y = mainTotal - (p.y + p.h);
      else p.x = mainTotal - (p.x + p.w);
    }
  }

  return graph.nodes.map((n) => {
    const p = pos.get(n.id)!;
    return {
      id: n.id,
      label: n.label,
      shape: n.shape,
      x: Math.round(p.x),
      y: Math.round(p.y),
      w: Math.round(p.w),
      h: Math.round(p.h),
    };
  });
}


function routeEdges(
  graph: FlowGraph,
  nodes: LaidNode[],
  byId: Map<string, LaidNode>,
  vertical: boolean,
): LaidEdge[] {
  const edges: LaidEdge[] = [];
  for (const e of graph.edges) {
    const a = byId.get(e.from);
    const b = byId.get(e.to);
    if (!a || !b) continue;
    if (e.from === e.to) {
      const r = selfLoopPath(a);
      edges.push({ ...e, path: r.path, lx: a.x + a.w + 22, ly: a.y + a.h / 2, selfLoop: true });
      continue;
    }
    const routed = routeAround(a, b, nodes, vertical) ?? routeBack(a, b, nodes, vertical)
      ?? edgePath(a, b, vertical);
    edges.push({
      ...e,
      path: routed.path,
      lx: (routed.sx + routed.ex) / 2,
      ly: (routed.sy + routed.ey) / 2,
      selfLoop: false,
    });
  }
  return edges;
}


function layoutGroups(graph: FlowGraph, byId: Map<string, LaidNode>): LaidGroup[] {
  const groupOf = new Map<string, string[]>();
  for (const n of graph.nodes) {
    const g = n.groups[n.groups.length - 1];
    if (!g) continue;
    if (!groupOf.has(g)) groupOf.set(g, []);
    groupOf.get(g)!.push(n.id);
  }
  const groups: LaidGroup[] = [];
  for (const g of graph.groups) {
    const members = groupOf.get(g.id) ?? [];
    if (!members.length) continue;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const id of members) {
      const n = byId.get(id)!;
      x0 = Math.min(x0, n.x);
      y0 = Math.min(y0, n.y);
      x1 = Math.max(x1, n.x + n.w);
      y1 = Math.max(y1, n.y + n.h);
    }
    groups.push({
      id: g.id,
      label: g.label,
      x: Math.round(x0 - GROUP_PAD),
      y: Math.round(y0 - GROUP_TITLE_H),
      w: Math.round(x1 - x0 + GROUP_PAD * 2),
      h: Math.round(y1 - y0 + GROUP_TITLE_H + GROUP_PAD),
    });
  }
  return groups;
}


function shiftPositive(nodes: LaidNode[], edges: LaidEdge[], groups: LaidGroup[]): void {
  let minX = Math.min(0, ...groups.map((g) => g.x));
  let minY = Math.min(0, ...groups.map((g) => g.y));
  for (const e of edges) {
    const b = pathBounds(e.path);
    if (!Number.isFinite(b.x0)) continue;
    minX = Math.min(minX, b.x0);
    minY = Math.min(minY, b.y0);
  }
  if (minX >= 0 && minY >= 0) return;
  const dx = -minX + 8;
  const dy = -minY + 8;
  for (const n of nodes) { n.x += dx; n.y += dy; }
  for (const e of edges) { e.lx += dx; e.ly += dy; e.path = shiftPath(e.path, dx, dy); }
  for (const g of groups) { g.x += dx; g.y += dy; }
}


function finish(
  graph: FlowGraph,
  nodes: LaidNode[],
  edges: LaidEdge[],
  groups: LaidGroup[],
): FlowLayout {
  let maxX = Math.max(0, ...nodes.map((n) => n.x + n.w), ...groups.map((g) => g.x + g.w));
  let maxY = Math.max(0, ...nodes.map((n) => n.y + n.h), ...groups.map((g) => g.y + g.h));
  for (const e of edges) {
    const b = pathBounds(e.path);
    if (!Number.isFinite(b.x1)) continue;
    maxX = Math.max(maxX, b.x1, e.lx);
    maxY = Math.max(maxY, b.y1, e.ly);
  }
  return {
    width: Math.round(maxX + 12),
    height: Math.round(maxY + 12),
    direction: graph.direction,
    nodes,
    edges,
    groups,
  };
}
