import { describe, expect, it } from "vitest";
import { parseFlowchart } from "./parser";

const p = (s: string) => {
  const g = parseFlowchart(s);
  if (!g) throw new Error("parse failed");
  return g;
};

describe("parseFlowchart 头部与方向", () => {
  it("识别 flowchart / graph 的方向", () => {
    expect(p("flowchart TD\n A-->B").direction).toBe("TD");
    expect(p("graph LR\n A-->B").direction).toBe("LR");
    expect(p("flowchart BT\n A-->B").direction).toBe("BT");
    expect(p("flowchart\n A-->B").direction).toBe("TD");
  });

  it("不是流程图返回 null", () => {
    expect(parseFlowchart("")).toBeNull();
    expect(parseFlowchart("sequenceDiagram\n A->>B: hi")).toBeNull();
  });
});

describe("parseFlowchart 节点形状", () => {
  it("各种括号对应各种形状", () => {
    const g = p(`flowchart TD
      A[矩形]
      B(圆角)
      C([体育场])
      D[[子程序]]
      E[(圆柱)]
      F((圆))
      G{菱形}
      H{{六边形}}
      I>旗标]
      J[/平行四边形/]`);
    const shape = (id: string) => g.nodes.find((n) => n.id === id)!.shape;
    expect(shape("A")).toBe("rect");
    expect(shape("B")).toBe("round");
    expect(shape("C")).toBe("stadium");
    expect(shape("D")).toBe("subroutine");
    expect(shape("E")).toBe("cylinder");
    expect(shape("F")).toBe("circle");
    expect(shape("G")).toBe("diamond");
    expect(shape("H")).toBe("hexagon");
    expect(shape("I")).toBe("flag");
    expect(shape("J")).toBe("parallelogram");
  });

  it("标签去引号、<br> 转换行、剥 HTML 实体", () => {
    const g = p('flowchart TD\n A["含 <b>粗</b><br>换行 &amp; 符号"]');
    expect(g.nodes[0].label).toBe("含 <b>粗</b>\n换行 & 符号");
  });

  it("只出现在边里的节点自动补全，标签默认是 id", () => {
    const g = p("flowchart TD\n A[开始] --> B --> C[结束]");
    expect(g.nodes.map((n) => n.id)).toEqual(["A", "B", "C"]);
    expect(g.nodes.find((n) => n.id === "B")!.label).toBe("B");
  });

  it("先占位后给标签时，标签会被补上", () => {
    const g = p("flowchart TD\n A --> B\n B[后来给的标签]");
    expect(g.nodes.find((n) => n.id === "B")!.label).toBe("后来给的标签");
  });
});

describe("parseFlowchart 边", () => {
  it("实线/虚线/粗线 + 箭头", () => {
    const g = p(`flowchart TD
      A --> B
      A -.-> C
      A ==> D
      A --- E`);
    const e = (to: string) => g.edges.find((x) => x.to === to)!;
    expect(e("B").style).toBe("solid");
    expect(e("B").head).toBe("arrow");
    expect(e("C").style).toBe("dotted");
    expect(e("D").style).toBe("thick");
    expect(e("E").head).toBe("none");
  });

  it("双向箭头与圆形/叉形端点", () => {
    const g = p(`flowchart TD
      A <--> B
      A --o C
      A --x D`);
    expect(g.edges.find((e) => e.to === "B")!.tailHead).toBe(true);
    expect(g.edges.find((e) => e.to === "C")!.head).toBe("circle");
    expect(g.edges.find((e) => e.to === "D")!.head).toBe("cross");
  });

  it("边标签：|文字| 与内联 -- 文字 -->", () => {
    const g = p(`flowchart TD
      A -->|是| B
      A -- 否 --> C
      A -. 也许 .-> D`);
    expect(g.edges.find((e) => e.to === "B")!.label).toBe("是");
    expect(g.edges.find((e) => e.to === "C")!.label).toBe("否");
    expect(g.edges.find((e) => e.to === "D")!.label).toBe("也许");
    expect(g.edges.find((e) => e.to === "D")!.style).toBe("dotted");
  });

  it("链式与 & 扇出", () => {
    const g = p("flowchart TD\n A --> B --> C\n X & Y --> Z");
    expect(g.edges.filter((e) => e.from === "A" && e.to === "B")).toHaveLength(1);
    expect(g.edges.some((e) => e.from === "B" && e.to === "C")).toBe(true);
    expect(g.edges.filter((e) => e.to === "Z").map((e) => e.from).sort()).toEqual(["X", "Y"]);
  });

  it("分号可分隔多条语句", () => {
    const g = p("flowchart TD\n A-->B; B-->C");
    expect(g.edges).toHaveLength(2);
  });
});

describe("parseFlowchart 分组与忽略项", () => {
  it("subgraph 记录成员所属分组，end 正确配对", () => {
    const g = p(`flowchart TD
      subgraph S1[第一组]
        A --> B
      end
      B --> C`);
    expect(g.groups.find((x) => x.id === "S1")!.label).toBe("第一组");
    expect(g.nodes.find((n) => n.id === "A")!.groups).toEqual(["S1"]);
    expect(g.nodes.find((n) => n.id === "C")!.groups).toEqual([]);
  });

  it("subgraph 内再次引用已定义节点时，该节点也算成员", () => {
    const g = p(`flowchart TD
      A[甲] --> B[乙]
      subgraph S[组]
        A
      end`);
    expect(g.nodes.find((n) => n.id === "A")!.groups).toEqual(["S"]);
    expect(g.nodes.find((n) => n.id === "B")!.groups).toEqual([]);
  });

  it("%% 注释与 classDef/style 被忽略", () => {
    const g = p(`flowchart TD
      %% 这是注释
      A --> B
      classDef warn fill:#f00
      class A warn
      style B fill:#0f0
      linkStyle 0 stroke:#00f`);
    expect(g.nodes).toHaveLength(2);
    expect(g.edges).toHaveLength(1);
  });
});
