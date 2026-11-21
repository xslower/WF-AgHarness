import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { RichMarkdown } from ".";

const html = (text: string) => renderToStaticMarkup(<RichMarkdown text={text} />);

describe("RichMarkdown 表格渲染", () => {
  it("渲染出 table/thead/tbody 结构", () => {
    const h = html("说明：\n\n| 名称 | 数量 |\n|:--|--:|\n| 苹果 | 3 |\n| 梨 | 12 |\n\n结束。");
    expect(h).toContain("<table>");
    expect(h).toContain("<thead>");
    expect(h).toContain("<tbody>");
    expect((h.match(/<tr>/g) || []).length).toBe(3); 
    expect(h).toContain('style="text-align:right"');
    expect(h).toContain("苹果");
    expect(h).toContain("说明：");
    expect(h).toContain("结束。");
  });

  it("单元格里的行内 markdown 生效且不套 p", () => {
    const h = html("| A | B |\n|---|---|\n| **粗** | `code` |");
    expect(h).toContain("<strong>粗</strong>");
    expect(h).toContain("<code>code</code>");
    expect(h).not.toContain("<td><p>");
  });

  it("代码块里的竖线不被当表格", () => {
    const h = html("```\n| A | B |\n|---|---|\n| 1 | 2 |\n```");
    expect(h).not.toContain("<table>");
    expect(h).toContain("md-copy"); 
  });
});
