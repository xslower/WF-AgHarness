
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { TodoPanel, todoCollapsed } from "./TodoPanel";

const html = (todos: { content: string; status: "done" | "pending" | "in_progress" }[]) =>
  renderToStaticMarkup(createElement(TodoPanel, { todos: todos as never }));

const done = (c: string) => ({ content: c, status: "done" as const });
const doing = (c: string) => ({ content: c, status: "in_progress" as const });

describe("todoCollapsed 折叠策略", () => {
  it("未全部完成 → 展开", () => {
    expect(todoCollapsed([done("a"), doing("b")], null)).toBe(false);
  });

  it("全部完成且用户没干预 → 收起", () => {
    expect(todoCollapsed([done("a"), done("b")], null)).toBe(true);
  });

  it("用户在已完成状态下点开 → 保持展开（不被立刻收回）", () => {
    expect(todoCollapsed([done("a"), done("b")], true)).toBe(false);
  });

  it("用户手动收起 → 收起", () => {
    expect(todoCollapsed([done("a")], false)).toBe(true);
  });

  it("空清单不算完成（不该渲染成收起的一行）", () => {
    expect(todoCollapsed([], null)).toBe(false);
  });
});

describe("TodoPanel 渲染", () => {
  it("全部完成时默认只显示摘要行，不列出条目", () => {
    const h = html([done("写测试"), done("跑门禁")]);
    expect(h).toContain("2/2 完成");
    expect(h).not.toContain("写测试");   
  });

  it("有未完成项时列出每条内容", () => {
    const h = html([done("写测试"), doing("跑门禁")]);
    expect(h).toContain("写测试");
    expect(h).toContain("跑门禁");
    expect(h).toContain("1/2 完成");
  });

  it("空清单不渲染任何东西", () => {
    expect(html([])).toBe("");
  });
});
