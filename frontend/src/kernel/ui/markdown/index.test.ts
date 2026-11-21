import { describe, expect, it } from "vitest";
import { mdText, splitMdTables } from ".";

describe("splitMdTables", () => {
  it("识别基础表格", () => {
    const src = "前文\n\n| A | B |\n|---|:-:|\n| 1 | 2 |\n| 3 | 4 |\n\n后文";
    const segs = splitMdTables(src);
    expect(segs.map((s) => s.type)).toEqual(["text", "table", "text"]);
    const t = segs[1];
    if (t.type !== "table") throw new Error("not table");
    expect(t.head).toEqual(["A", "B"]);
    expect(t.align).toEqual([undefined, "center"]);
    expect(t.rows).toEqual([["1", "2"], ["3", "4"]]);
  });

  it("支持无首尾竖线、对齐与转义竖线", () => {
    const segs = splitMdTables("A | B | C\n:--|--:|:-:\nx \\| y | ``2`` | **3**");
    expect(segs).toHaveLength(1);
    const t = segs[0];
    if (t.type !== "table") throw new Error("not table");
    expect(t.align).toEqual(["left", "right", "center"]);
    expect(t.rows[0]).toEqual(["x | y", "``2``", "**3**"]);
  });

  it("缺列补齐、多列截断", () => {
    const segs = splitMdTables("| A | B |\n|---|---|\n| 1 |\n| 1 | 2 | 3 |");
    const t = segs[0];
    if (t.type !== "table") throw new Error("not table");
    expect(t.rows).toEqual([["1", ""], ["1", "2"]]);
  });

  it("代码围栏内的表格不解析", () => {
    const src = "```md\n| A | B |\n|---|---|\n| 1 | 2 |\n```";
    expect(splitMdTables(src).map((s) => s.type)).toEqual(["text"]);
  });

  it("分隔行不合法时按普通文本", () => {
    const src = "| A | B |\n| x | y |";
    expect(splitMdTables(src).map((s) => s.type)).toEqual(["text"]);
  });

  it("表格后紧跟段落会正确结束", () => {
    const segs = splitMdTables("| A |\n|---|\n| 1 |\n普通段落");
    expect(segs.map((s) => s.type)).toEqual(["table", "text"]);
  });

  it("mdText 去缩进不影响表格识别", () => {
    const segs = splitMdTables(mdText("  | A | B |\n  |---|---|\n  | 1 | 2 |"));
    expect(segs.map((s) => s.type)).toEqual(["table"]);
  });
});
