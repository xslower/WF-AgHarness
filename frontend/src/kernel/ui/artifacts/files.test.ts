
import { describe, expect, it } from "vitest";
import { baseName, tabFromPreview, tabKind } from "./files";

describe("tabKind", () => {
  it("后端判为图片就以图片渲染（不猜扩展名）", () => {
    expect(tabKind("logo.bin", "image")).toBe("image");
  });

  it("按扩展名分档：md / 代码 / 其余当纯文本", () => {
    expect(tabKind("report.md")).toBe("md");
    expect(tabKind("main.py")).toBe("code");
    expect(tabKind("notes.txt")).toBe("text");
    expect(tabKind("README")).toBe("text");   
  });

  it("大写扩展名也认", () => {
    expect(tabKind("INDEX.MD")).toBe("md");
    expect(tabKind("App.TSX")).toBe("code");
  });
});

describe("baseName", () => {
  it("斜杠与反斜杠都能取文件名（Windows 路径）", () => {
    expect(baseName("out/a/b.md")).toBe("b.md");
    expect(baseName("C:\\work\\out\\b.md")).toBe("b.md");
    expect(baseName("plain.md")).toBe("plain.md");
  });
});

describe("tabFromPreview", () => {
  it("Markdown 默认预览态，标题取文件名", () => {
    const t = tabFromPreview("/p/out/report.md", { kind: "text", content: "# hi" });
    expect(t.key).toBe("/p/out/report.md");
    expect(t.title).toBe("report.md");
    expect(t.kind).toBe("md");
    expect(t.mdPreview).toBe(true);
    expect(t.content).toBe("# hi");
  });

  it("代码文件不带 mdPreview（否则代码区会渲染成 md）", () => {
    const t = tabFromPreview("/p/a.py", { kind: "text", content: "print(1)" });
    expect(t.kind).toBe("code");
    expect(t.ext).toBe("py");
    expect(t.mdPreview).toBe(false);
  });

  it("图片带 dataurl", () => {
    const t = tabFromPreview("/p/x.png", { kind: "image", dataurl: "data:image/png;base64,AA" });
    expect(t.kind).toBe("image");
    expect(t.dataurl).toContain("base64");
  });
});
