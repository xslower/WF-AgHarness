
import { describe, expect, it } from "vitest";
import type { Edge, Node } from "@xyflow/react";
import { buildSubflow, uniqueName } from "./extract";
import { extractChain } from "./graphOps";

const node = (id: string, dsl: Record<string, unknown> = {}, pos = { x: 0, y: 0 }): Node => ({
  id, type: "dsl", position: pos, data: { dsl: { id, ...dsl } },
} as Node);

const edge = (source: string, target: string, sourceHandle?: string): Edge => ({
  id: `${source}-${sourceHandle ?? "out"}-${target}`, source, target, sourceHandle,
} as Edge);


function chain4(): { nodes: Node[]; edges: Edge[] } {
  return {
    nodes: [
      node("n1", { type: "llm", prompt: "起：${inputs.text}", next: "n2" }),
      node("n2", { type: "llm", prompt: "中：${prev}", next: "n3" }),
      node("n3", { type: "write", path: "a.md", content: "${prev}", next: "n4" }),
      node("n4", { type: "handoff" }),
    ],
    edges: [edge("n1", "n2"), edge("n2", "n3"), edge("n3", "n4")],
  };
}

describe("extractChain", () => {
  it("沿单入单出主线下取整段", () => {
    const { nodes, edges } = chain4();
    expect(extractChain(nodes, edges, "n2")).toEqual(["n2", "n3", "n4"]);
  });

  it("遇到分叉就停（控制节点两出口不能整段抽）", () => {
    const nodes = [
      node("a", { type: "llm" }), node("c", { type: "condition" }),
      node("t", { type: "llm" }), node("f", { type: "llm" }),
    ];
    const edges = [edge("a", "c"), edge("c", "t", "true"), edge("c", "f", "false")];
    expect(extractChain(nodes, edges, "a")).toEqual(["a"]);   
  });

  it("汇合点不收（否则会把别人的上游切走）", () => {
    const nodes = [node("a", { type: "llm" }), node("x", { type: "llm" }), node("j", { type: "llm" })];
    const edges = [edge("a", "j"), edge("x", "j")];
    expect(extractChain(nodes, edges, "a")).toEqual(["a"]);
  });

  it("回边不跟进，不会死循环", () => {
    const nodes = [node("a", { type: "llm" }), node("b", { type: "llm" })];
    const edges = [edge("a", "b"), edge("b", "a")];
    expect(extractChain(nodes, edges, "a")).toEqual(["a", "b"]);
  });
});

describe("buildSubflow", () => {
  it("整段搬进子工作流，父图换成一个 workflow 节点并接上前后", () => {
    const { nodes, edges } = chain4();
    const res = buildSubflow(nodes, edges, "n2", "子段", "w9");
    expect(res).not.toBeNull();
    const r = res!;

    
    expect(r.sub.nodes.map((n) => n.id)).toEqual(["n2", "n3", "n4"]);
    expect(r.sub.edges.map((e) => `${e.source}->${e.target}`))
      .toEqual(["n2->n3", "n3->n4"]);
    
    expect(String(r.sub.nodes[0].prompt)).toContain("${inputs.input}");
    expect(String(r.sub.nodes[1].content)).toContain("${prev}");   
    
    expect(r.sub.nodes.every((n) => n.pos === undefined)).toBe(true);

    
    expect(r.nodes.map((n) => n.id).sort()).toEqual(["n1", "w9"]);
    const wf = r.nodes.find((n) => n.id === "w9")!;
    expect((wf.data as any).dsl).toMatchObject({
      type: "workflow", name: "子段", output: "final",
    });
    expect(JSON.parse((wf.data as any).dsl.inputsJson)).toEqual({ input: "${prev}" });
    expect(r.edges.map((e) => `${e.source}->${e.target}`)).toEqual(["n1->w9"]);
    expect(r.moved).toEqual(["n2", "n3", "n4"]);
  });

  it("段尾若原本接回父图，父图仍能从新节点接出去", () => {
    
    const nodes = [
      node("a", { type: "llm" }), node("b", { type: "llm" }),
      node("c", { type: "llm" }), node("x", { type: "llm" }),
    ];
    const edges = [edge("a", "b"), edge("b", "c"), edge("x", "c")];
    const r = buildSubflow(nodes, edges, "b", "子", "w1")!;
    expect(r.moved).toEqual(["b"]);
    expect(r.edges.map((e) => `${e.source}->${e.target}`).sort())
      .toEqual(["a->w1", "w1->c", "x->c"]);
  });

  it("起点就是末端单节点也能抽，但不会凭空接出边", () => {
    const nodes = [node("a", { type: "llm" }), node("end", { type: "handoff" })];
    const edges = [edge("a", "end")];
    const r = buildSubflow(nodes, edges, "end", "尾巴", "w2")!;
    expect(r.moved).toEqual(["end"]);
    expect(r.edges.map((e) => `${e.source}->${e.target}`)).toEqual(["a->w2"]);
  });

  it("节点不存在时返回 null", () => {
    expect(buildSubflow([], [], "nope", "x", "w")).toBeNull();
  });
});

describe("uniqueName", () => {
  it("重名自动加后缀", () => {
    expect(uniqueName("片段", [])).toBe("片段");
    expect(uniqueName("片段", ["片段"])).toBe("片段-2");
    expect(uniqueName("片段", ["片段", "片段-2"])).toBe("片段-3");
  });
});
