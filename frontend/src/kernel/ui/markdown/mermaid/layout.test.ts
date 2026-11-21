import { describe, expect, it } from "vitest";
import { parseFlowchart } from "./parser";
import { layoutFlow, measureNode, wrapLabel } from "./layout";

const lay = (src: string) => {
  const g = parseFlowchart(src);
  if (!g) throw new Error("parse failed");
  return layoutFlow(g);
};


function overlaps(a: { x: number; y: number; w: number; h: number }, b: typeof a) {
  return a.x < b.x + b.w - 1 && b.x < a.x + a.w - 1 && a.y < b.y + b.h - 1 && b.y < a.y + a.h - 1;
}

describe("wrapLabel / measureNode", () => {
  it("长标签会折行，短标签不折", () => {
    expect(wrapLabel("短")).toEqual(["短"]);
    expect(wrapLabel("这是一段很长很长很长很长很长很长的说明文字").length).toBeGreaterThan(1);
  });

  it("显式换行被保留", () => {
    expect(wrapLabel("第一行\n第二行")).toEqual(["第一行", "第二行"]);
  });

  it("菱形比矩形更宽更高（留出内接空间）", () => {
    const r = measureNode("判断条件", "rect");
    const d = measureNode("判断条件", "diamond");
    expect(d.w).toBeGreaterThan(r.w);
    expect(d.h).toBeGreaterThan(r.h);
  });

  it("圆是正方形外接盒", () => {
    const c = measureNode("圆", "circle");
    expect(c.w).toBe(c.h);
  });
});

describe("layoutFlow 分层", () => {
  it("TD：按入边方向自上而下分层", () => {
    const l = lay("flowchart TD\n A --> B\n B --> C");
    const y = (id: string) => l.nodes.find((n) => n.id === id)!.y;
    expect(y("A")).toBeLessThan(y("B"));
    expect(y("B")).toBeLessThan(y("C"));
    
    const cx = (id: string) => {
      const n = l.nodes.find((x) => x.id === id)!;
      return n.x + n.w / 2;
    };
    expect(Math.abs(cx("A") - cx("B"))).toBeLessThan(1);
  });

  it("LR：沿横向分层", () => {
    const l = lay("flowchart LR\n A --> B");
    const x = (id: string) => l.nodes.find((n) => n.id === id)!.x;
    expect(x("A")).toBeLessThan(x("B"));
  });

  it("BT 是 TD 的上下翻转", () => {
    const l = lay("flowchart BT\n A --> B");
    const y = (id: string) => l.nodes.find((n) => n.id === id)!.y;
    expect(y("A")).toBeGreaterThan(y("B"));
  });

  it("同层节点不重叠", () => {
    const l = lay("flowchart TD\n A --> B & C & D\n B --> E\n C --> E\n D --> E");
    for (let i = 0; i < l.nodes.length; i++) {
      for (let j = i + 1; j < l.nodes.length; j++) {
        expect(overlaps(l.nodes[i], l.nodes[j])).toBe(false);
      }
    }
  });

  it("有环也不会死循环，且所有节点都有坐标", () => {
    const l = lay("flowchart TD\n A --> B\n B --> C\n C --> A");
    expect(l.nodes).toHaveLength(3);
    for (const n of l.nodes) {
      expect(Number.isFinite(n.x)).toBe(true);
      expect(Number.isFinite(n.y)).toBe(true);
    }
  });

  it("自环被单独处理，不会产生 NaN 路径", () => {
    const l = lay("flowchart TD\n A --> A\n A --> B");
    const self = l.edges.find((e) => e.from === "A" && e.to === "A")!;
    expect(self.selfLoop).toBe(true);
    expect(self.path).not.toContain("NaN");
  });

  it("画布尺寸包住所有节点与分组", () => {
    const l = lay("flowchart TD\n subgraph S[组]\n A --> B\n end\n B --> C[很长很长很长很长的节点标签文字]");
    for (const n of l.nodes) {
      expect(n.x + n.w).toBeLessThanOrEqual(l.width);
      expect(n.y + n.h).toBeLessThanOrEqual(l.height);
    }
    const g = l.groups[0];
    expect(g).toBeTruthy();
    expect(g.x + g.w).toBeLessThanOrEqual(l.width);
  });

  it("所有坐标非负（分组框的负边距会被平移消除）", () => {
    const l = lay("flowchart TD\n subgraph S[组]\n A --> B\n end");
    expect(l.nodes.every((n) => n.x >= 0 && n.y >= 0)).toBe(true);
    expect(l.groups.every((g) => g.x >= 0 && g.y >= 0)).toBe(true);
  });

  it("边路径都从 from 指向 to，且不含 NaN", () => {
    const l = lay("flowchart TD\n A --> B\n B --> C\n A -->|跳过| C");
    for (const e of l.edges) {
      expect(e.path).toMatch(/^M[\d.-]+,[\d.-]+/);
      expect(e.path).not.toContain("NaN");
    }
    expect(l.edges.find((e) => e.label === "跳过")!.label).toBe("跳过");
  });

  it("孤立节点也能布局", () => {
    const l = lay("flowchart TD\n A[孤立]");
    expect(l.nodes).toHaveLength(1);
    expect(l.width).toBeGreaterThan(0);
  });
});
