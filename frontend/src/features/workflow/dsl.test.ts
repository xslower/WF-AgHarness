
import { describe, expect, it } from "vitest";
import type { Edge, Node } from "@xyflow/react";
import type { WorkflowDef } from "../../kernel/api";
import { canvasToDsl, dslToCanvas } from "./dsl";

const wf: WorkflowDef = {
  name: "t",
  desc: "",
  nodes: [
    { id: "s1", type: "llm", prompt: "hi", next: "c1" },
    { id: "c1", type: "condition", expr: "len(x) > 0", true: "s2", false: "s3" },
    { id: "s2", type: "write", path: "a.md", content: "A" },
    { id: "s3", type: "write", path: "b.md", content: "B" },
  ],
} as unknown as WorkflowDef;

describe("dslToCanvas", () => {
  it("旧 DSL（无 edges）自动生成连线：next/true/false", () => {
    const { nodes, edges } = dslToCanvas(wf);
    expect(nodes).toHaveLength(4);
    
    expect(edges).toHaveLength(3);
    const trueEdge = edges.find((e) => e.sourceHandle === "true");
    expect(trueEdge?.source).toBe("c1");
    expect(trueEdge?.target).toBe("s2");
    const falseEdge = edges.find((e) => e.sourceHandle === "false");
    expect(falseEdge?.target).toBe("s3");
  });

  it("节点携带 dsl 数据与画布坐标", () => {
    const { nodes } = dslToCanvas(wf);
    const s1 = nodes.find((n) => n.id === "s1");
    expect(s1?.type).toBe("dsl");
    expect((s1?.data as { dsl: Record<string, unknown> }).dsl.type).toBe("llm");
    expect(s1?.position.x).toBeGreaterThanOrEqual(0);
    expect(s1?.position.y).toBeGreaterThanOrEqual(0);
  });
});

describe("canvasToDsl", () => {
  it("画布 → DSL → 画布 往返保持连线一致", () => {
    const c1 = dslToCanvas(wf);
    const back = canvasToDsl(wf, c1.nodes, c1.edges);
    expect(back.edges).toHaveLength(3);
    const c2 = dslToCanvas(back);
    expect(c2.edges).toHaveLength(3);
    const key = (e: Edge) => `${e.source}-${e.sourceHandle ?? "out"}-${e.target}`;
    expect(c2.edges.map(key).sort()).toEqual(c1.edges.map(key).sort());
  });

  it("condition 节点从连线恢复 true/false 目标", () => {
    const c1 = dslToCanvas(wf);
    const back = canvasToDsl(wf, c1.nodes, c1.edges);
    const cond = back.nodes.find((n) => n.id === "c1") as unknown as Record<string, unknown>;
    expect(cond.true).toBe("s2");
    expect(cond.false).toBe("s3");
  });

  it("保存画布坐标到 pos 字段", () => {
    const c1 = dslToCanvas(wf);
    const moved: Node[] = c1.nodes.map((n) =>
      n.id === "s1" ? { ...n, position: { x: 555.6, y: 777.2 } } : n);
    const back = canvasToDsl(wf, moved, c1.edges);
    const s1 = back.nodes.find((n) => n.id === "s1") as unknown as Record<string, unknown>;
    expect(s1.pos).toBe("556,777");
  });
});
