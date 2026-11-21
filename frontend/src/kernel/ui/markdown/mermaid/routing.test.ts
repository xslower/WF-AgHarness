import { describe, expect, it } from "vitest";
import { parseFlowchart } from "./parser";
import { layoutFlow } from "./layout";

const lay = (src: string) => {
  const g = parseFlowchart(src);
  if (!g) throw new Error("parse failed");
  return layoutFlow(g);
};


function crossingNodes(path: string, nodes: { id: string; x: number; y: number; w: number; h: number }[]) {
  
  const nums = [...path.matchAll(/(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g)].map((m) => ({
    x: parseFloat(m[1]),
    y: parseFloat(m[2]),
  }));
  const pts: { x: number; y: number }[] = [];
  for (let i = 0; i + 1 < nums.length; i++) {
    const a = nums[i], b = nums[i + 1];
    const dist = Math.hypot(b.x - a.x, b.y - a.y);
    const steps = Math.max(1, Math.ceil(dist / 2));
    for (let s = 0; s <= steps; s++) {
      pts.push({ x: a.x + ((b.x - a.x) * s) / steps, y: a.y + ((b.y - a.y) * s) / steps });
    }
  }
  const inside = (p: { x: number; y: number }, n: { x: number; y: number; w: number; h: number }) =>
    p.x > n.x + 1 && p.x < n.x + n.w - 1 && p.y > n.y + 1 && p.y < n.y + n.h - 1;
  const near = (p: { x: number; y: number }, n: { x: number; y: number; w: number; h: number }) =>
    p.x > n.x - 2 && p.x < n.x + n.w + 2 && p.y > n.y - 2 && p.y < n.y + n.h + 2;
  const first = pts[0], last = pts[pts.length - 1];
  return nodes
    .filter((n) => !near(first, n) && !near(last, n) && pts.some((p) => inside(p, n)))
    .map((n) => n.id);
}

const CHAIN = `flowchart TD
  U[用户消息] --> R{只读模式?}
  R -->|是| P[先出计划]
  R -->|否| T[调用工具]
  P --> OK[用户确认]
  OK --> T
  T --> S{成功?}
  S -->|否| E[降级重试]
  E --> T
  S -->|是| D[写文件]
  D --> DONE[完成]`;

describe("长边绕行（不穿节点）", () => {
  it("向前的跨层边绕开中间层节点", () => {
    const l = lay(CHAIN);
    const e = l.edges.find((x) => x.from === "R" && x.to === "T")!;
    expect(crossingNodes(e.path, l.nodes)).toEqual([]);
  });

  it("向后的回退边走外侧通道，不横穿中间层", () => {
    const l = lay(CHAIN);
    const e = l.edges.find((x) => x.from === "E" && x.to === "T")!;
    expect(crossingNodes(e.path, l.nodes)).toEqual([]);
  });

  it("整张图的每条边都不穿节点", () => {
    const l = lay(CHAIN);
    for (const e of l.edges) {
      expect(crossingNodes(e.path, l.nodes), `${e.from}->${e.to}`).toEqual([]);
    }
  });

  it("绕行路径不会跑到画布外", () => {
    const l = lay(CHAIN);
    for (const e of l.edges) {
      const xs = [...e.path.matchAll(/(-?\d+(?:\.\d+)?),/g)].map((m) => parseFloat(m[1]));
      const ys = [...e.path.matchAll(/,(-?\d+(?:\.\d+)?)/g)].map((m) => parseFloat(m[1]));
      expect(Math.min(...xs)).toBeGreaterThanOrEqual(0);
      expect(Math.min(...ys)).toBeGreaterThanOrEqual(0);
      expect(Math.max(...xs)).toBeLessThanOrEqual(l.width);
      expect(Math.max(...ys)).toBeLessThanOrEqual(l.height);
    }
  });

  it("简单的相邻层直边不绕（保持直线，观感更干净）", () => {
    const l = lay("flowchart TD\n A --> B");
    const e = l.edges[0];
    expect((e.path.match(/L/g) || []).length).toBe(1); 
  });
});
