
import { describe, expect, it } from "vitest";
import type { Connection, Edge } from "@xyflow/react";
import {
  NODE_DEFAULTS, buildNodeDsl, canAddNode, connectEdges, nodeId, placeNewNode, removeNode,
} from "./graphOps";
import type { PaletteItem } from "./Palette";
import { WF_NODE_DEFAULT_SPEC } from "../../kernel/model/modelSpec";

const item = (over: Partial<PaletteItem> = {}): PaletteItem => ({
  type: "llm", label: "LLM", desc: "", icon: "🤖", group: "LLM", fields: [], ...over,
} as PaletteItem);

const conn = (over: Partial<Connection> = {}): Connection =>
  ({ source: "a", target: "b", sourceHandle: null, targetHandle: null, ...over } as Connection);

const edge = (over: Partial<Edge> = {}): Edge =>
  ({ id: "e", source: "a", target: "b", ...over } as Edge);

describe("nodeId", () => {
  it("tool 用 f 前缀，其余取类型首字母", () => {
    expect(nodeId("tool", 3)).toBe("f3");
    expect(nodeId("llm", 1)).toBe("l1");
    expect(nodeId("write", 7)).toBe("w7");
    expect(nodeId("web_search", 2)).toBe("w2");
  });
});

describe("canAddNode", () => {
  it("编排模式只允许 llm", () => {
    expect(canAddNode(true, "llm")).toBe(true);
    expect(canAddNode(true, "tool")).toBe(false);
    expect(canAddNode(false, "tool")).toBe(true);
  });
});

describe("buildNodeDsl", () => {
  it("按字段声明填默认空值，select 取首项", () => {
    const dsl = buildNodeDsl(item({
      type: "custom",
      fields: [
        { key: "text", label: "文本", kind: "text" },
        { key: "mode", label: "模式", kind: "select", opts: ["fast", "slow"] },
      ] as any,
    }), "c1");
    expect(dsl).toMatchObject({ id: "c1", type: "custom", text: "", mode: "fast" });
  });

  it("select 无选项时填空串", () => {
    const dsl = buildNodeDsl(item({
      type: "custom",
      fields: [{ key: "mode", label: "m", kind: "select" }] as any,
    }), "c1");
    expect(dsl.mode).toBe("");
  });

  it("已有值不被字段默认值覆盖（preset 优先）", () => {
    const dsl = buildNodeDsl(item({
      type: "custom",
      preset: { text: "预设" },
      fields: [{ key: "text", label: "t", kind: "text" }] as any,
    }), "c1");
    expect(dsl.text).toBe("预设");
  });

  it("extra 覆盖 preset", () => {
    const dsl = buildNodeDsl(item({ type: "code", preset: { lang: "js" } }), "c1",
                            { lang: "python" });
    expect(dsl.lang).toBe("python");
  });

  it("NODE_DEFAULTS 只填空字段，不覆盖已有值", () => {
    const dsl = buildNodeDsl(item({ type: "write" }), "w1");
    expect(dsl.path).toBe(NODE_DEFAULTS.write.path);
    const dsl2 = buildNodeDsl(item({ type: "write" }), "w1", { path: "自定义.md" });
    expect(dsl2.path).toBe("自定义.md");
    expect(dsl2.content).toBe(NODE_DEFAULTS.write.content);
  });

  it("llm 预填 prompt 模板", () => {
    expect(buildNodeDsl(item({ type: "llm" }), "l1").prompt).toBe(NODE_DEFAULTS.llm.prompt);
  });

  it("llm / condition / subagent 三类节点新建时预填默认总结队列", () => {
    for (const type of ["llm", "condition", "subagent"]) {
      const dsl = buildNodeDsl(item({ type }), "x1");
      expect(dsl.model).toBe(WF_NODE_DEFAULT_SPEC);
      expect(dsl.model).toBe("summary");
    }
    
    expect(WF_NODE_DEFAULT_SPEC).not.toBe("parent");
  });

  it("mcp / tool 节点 argsJson 默认 {}", () => {
    const mcp = buildNodeDsl(item({ type: "mcp", fields: [{ key: "argsJson", label: "a", kind: "textarea" }] as any }), "m1");
    expect(mcp.argsJson).toBe("{}");
    const tool = buildNodeDsl(item({ type: "tool", fields: [{ key: "argsJson", label: "a", kind: "textarea" }] as any }), "f1");
    expect(tool.argsJson).toBe("{}");
    
    const filled = buildNodeDsl(item({ type: "tool" }), "f1", { argsJson: '{"a":1}' });
    expect(filled.argsJson).toBe('{"a":1}');
  });

  it("未知节点类型不加默认值", () => {
    const dsl = buildNodeDsl(item({ type: "unknown_xyz" }), "u1");
    expect(Object.keys(dsl).sort()).toEqual(["id", "type"]);
  });
});

describe("placeNewNode", () => {
  it("三列错开，超过三个换行", () => {
    expect(placeNewNode(0)).toEqual({ x: 100, y: 90 });
    expect(placeNewNode(1)).toEqual({ x: 420, y: 90 });
    expect(placeNewNode(2)).toEqual({ x: 740, y: 90 });
    expect(placeNewNode(3)).toEqual({ x: 100, y: 260 });
  });
});

describe("connectEdges", () => {
  it("普通连线新增一条，id 带 handle", () => {
    const out = connectEdges([], conn());
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ id: "a-out-b", source: "a", target: "b" });
  });

  it("自连 / 缺 source / 缺 target 一律忽略", () => {
    expect(connectEdges([], conn({ source: "a", target: "a" }))).toEqual([]);
    expect(connectEdges([], conn({ source: null as any }))).toEqual([]);
    expect(connectEdges([], conn({ target: null as any }))).toEqual([]);
  });

  it("完全相同的边去重（同 source/handle/target）", () => {
    const base = connectEdges([], conn());
    expect(connectEdges(base, conn())).toBe(base);
  });

  it("同一对节点不同 handle 允许共存", () => {
    const base = connectEdges([], conn({ sourceHandle: "true" }));
    const out = connectEdges(base, conn({ sourceHandle: "false" }));
    expect(out).toHaveLength(2);
  });

  it("条件节点 true 只能有一条，第二条替换第一条", () => {
    const base = connectEdges([], conn({ sourceHandle: "true", target: "b" }));
    const out = connectEdges(base, conn({ sourceHandle: "true", target: "c" }));
    expect(out).toHaveLength(1);
    expect(out[0].target).toBe("c");
  });

  it("条件节点 true 与 false 互不影响", () => {
    const base = connectEdges([], conn({ sourceHandle: "true", target: "b" }));
    const out = connectEdges(base, conn({ sourceHandle: "false", target: "b" }));
    expect(out.map((e) => e.sourceHandle).sort()).toEqual(["false", "true"]);
  });

  it("普通节点允许并行多条出边", () => {
    const base = connectEdges([], conn({ target: "b" }));
    const out = connectEdges(base, conn({ target: "c" }));
    expect(out).toHaveLength(2);
  });
});

describe("removeNode", () => {
  it("同时删掉作为起点和终点的边", () => {
    const edges = [
      edge({ id: "1", source: "a", target: "b" }),
      edge({ id: "2", source: "b", target: "c" }),
      edge({ id: "3", source: "c", target: "d" }),
    ];
    const out = removeNode(edges, "b");
    expect(out.map((e) => e.id)).toEqual(["3"]);
  });

  it("没有关联边时原样返回", () => {
    const edges = [edge({ id: "1" })];
    expect(removeNode(edges, "zz")).toHaveLength(1);
  });
});
