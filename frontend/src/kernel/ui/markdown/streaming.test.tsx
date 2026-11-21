
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { RichMarkdown, StreamingMarkdown, splitStableBlocks, splitMdTables, mdText } from ".";

const norm = (s: string) => s.replace(/>\s+</g, "><").trim();
const html = (text: string) =>
  norm(renderToStaticMarkup(createElement(RichMarkdown, { text })));
const streamHtml = (text: string) =>
  norm(renderToStaticMarkup(createElement(StreamingMarkdown, { text, streaming: true })));

describe("splitStableBlocks", () => {
  it("按空行切块，不丢内容", () => {
    const blocks = splitStableBlocks("a\n\nb\n\nc");
    const joined = blocks.join("");
    expect(joined).toContain("a");
    expect(joined).toContain("c");
    expect(blocks.length).toBeGreaterThanOrEqual(2);
  });

  it("**围栏代码块里的空行不切**", () => {
    const blocks = splitStableBlocks("前\n\n```ts\nconst a = 1;\n\nconst b = 2;\n```");
    const codeBlock = blocks.find((b) => b.includes("```ts"));
    expect(codeBlock).toBeTruthy();
    expect(codeBlock!.includes("const b = 2;")).toBe(true);
  });

  it("空文本 → 空数组", () => {
    expect(splitStableBlocks("")).toEqual([]);
  });

  it("单段无空行 → 一块", () => {
    expect(splitStableBlocks("只有一段")).toEqual(["只有一段"]);
  });
});

describe("StreamingMarkdown 渲染结果", () => {
  const cases: Record<string, string> = {
    "纯段落": "第一段。\n\n第二段 **粗体**。\n\n第三段 `code`。",
    "带表格": "说明\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n后续",
    "带围栏代码": "前\n\n```ts\nconst a = 1;\n\nconst b = 2;\n```\n\n后",
    "中途有标题": "## 标题\n\n正文\n\n### 小标题\n\n更多正文",
  };

  for (const [name, text] of Object.entries(cases)) {
    it(name + "：与全量渲染结构一致", () => {
      expect(streamHtml(text)).toBe(html(text));
    });
  }

  it("流式逐字符追加不会崩，最后一步与全量一致", () => {
    const full = "第一段内容。\n\n第二段，含 **粗体**。\n\n```ts\nconst a = 1;\n```\n\n结尾段。";
    let acc = "";
    for (const ch of full) {
      acc += ch;
      expect(() => streamHtml(acc)).not.toThrow();
    }
    expect(streamHtml(acc)).toBe(html(full));
  });

  it("streaming=false 等同于 RichMarkdown", () => {
    const t = "a\n\n| x | y |\n|---|---|\n| 1 | 2 |";
    expect(norm(renderToStaticMarkup(createElement(StreamingMarkdown, { text: t }))))
      .toBe(html(t));
  });
});

describe("增量解析的收益", () => {
  it("切块后单块解析成本远低于整篇", () => {
    const para = (i: number) => `第 ${i} 段内容，含 **粗体** 与 \`code\`。`;
    const big = Array.from({ length: 200 }, (_, i) => para(i)).join("\n\n");

    const t0 = performance.now();
    splitMdTables(mdText(big));
    const fullMs = performance.now() - t0;

    const blocks = splitStableBlocks(big);
    expect(blocks.length).toBeGreaterThan(100);
    const t1 = performance.now();
    splitMdTables(mdText(blocks[blocks.length - 1]));
    const blockMs = performance.now() - t1;

    
    expect(blockMs).toBeLessThan(fullMs);
  });
});
