
import { describe, expect, it } from "vitest";
import { pickRunProject } from "./runProject";

describe("pickRunProject", () => {
  const all = ["/p/a", "/p/b", "/p/c"];

  it("优先用这条编排上次真实跑过的项目（唯一保证日志有内容的选项）", () => {
    expect(pickRunProject({ lastProject: "/p/b", current: "/p/a", all })).toBe("/p/b");
  });

  it("上次跑的项目已不在项目列表里 → 退回当前选择", () => {
    expect(pickRunProject({ lastProject: "/p/gone", current: "/p/c", all })).toBe("/p/c");
  });

  it("从没跑过 → 保持当前选择（含 localStorage 记忆）", () => {
    expect(pickRunProject({ lastProject: "", current: "/p/b", all })).toBe("/p/b");
  });

  it("都没有 → 项目树第一个", () => {
    expect(pickRunProject({ lastProject: "", current: "", all })).toBe("/p/a");
  });

  it("一个项目都没有 → 空串（顶栏显示「未选」，运行时拦截）", () => {
    expect(pickRunProject({ lastProject: "", current: "", all: [] })).toBe("");
  });

  it("当前选择不在列表里（项目被移除）→ 不返回失效路径", () => {
    expect(pickRunProject({ lastProject: "", current: "/p/gone", all })).toBe("/p/a");
  });
});
