import { describe, expect, it } from "vitest";
import { updateNodeDeep } from "./useFileTree";

interface N { path: string; isDir?: boolean; children?: N[]; [k: string]: unknown }

const tree = (): N[] => [
  {
    path: "/p/src", isDir: true, children: [
      { path: "/p/src/a", isDir: true, children: [] },
      { path: "/p/src/b.md" },
    ],
  },
  { path: "/p/readme.md" },
];

describe("updateNodeDeep（深层目录塞 children）", () => {
  it("能改到第 3 层节点", () => {
    const next = updateNodeDeep(tree(), "/p/src/a",
      (n) => ({ ...n, children: [{ path: "/p/src/a/deep.md" }] }));
    expect(next[0].children![0].children).toEqual([{ path: "/p/src/a/deep.md" }]);
  });

  it("沿路径的每一层都是新对象（否则 React 看不到变化）", () => {
    const orig = tree();
    const next = updateNodeDeep(orig, "/p/src/a", (n) => ({ ...n, children: [{ path: "x" }] }));
    expect(next).not.toBe(orig);
    expect(next[0]).not.toBe(orig[0]);
    expect(next[0].children).not.toBe(orig[0].children);
    expect(next[0].children![0]).not.toBe(orig[0].children![0]);
  });

  it("没改到的分支保持同一引用（避免整棵树重建）", () => {
    const orig = tree();
    const next = updateNodeDeep(orig, "/p/src/a", (n) => ({ ...n, children: [] }));
    expect(next[1]).toBe(orig[1]);              
    expect(next[0].children![1]).toBe(orig[0].children![1]);
  });

  it("路径不存在时原样返回（同一引用）", () => {
    const orig = tree();
    expect(updateNodeDeep(orig, "/p/nope", (n) => ({ ...n }))).toBe(orig);
  });

  it("能改到叶子节点", () => {
    const next = updateNodeDeep(tree(), "/p/readme.md", (n) => ({ ...n, isDir: true }));
    expect(next[1].isDir).toBe(true);
  });

  it("children 为空数组时不会误判成命中", () => {
    const orig: N[] = [{ path: "/a", isDir: true, children: [] }];
    const next = updateNodeDeep(orig, "/a", (n) => ({ ...n, children: [{ path: "/a/b" }] }));
    expect(next[0].children).toEqual([{ path: "/a/b" }]);
  });
});
