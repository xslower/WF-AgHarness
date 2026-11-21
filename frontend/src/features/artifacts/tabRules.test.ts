
import { describe, expect, it } from "vitest";
import { closeTabIn, normalizeUrl, patchTabIn, pushTab, urlTab } from "./tabRules";
import type { Tab } from "../../kernel/ui/artifacts/types";

const t = (key: string): Tab => ({ key, title: key, kind: "text" });

describe("pushTab", () => {
  it("同 key 幂等，不产生重复标签", () => {
    const once = pushTab([], t("/a"));
    expect(pushTab(once, t("/a"))).toHaveLength(1);
  });

  it("不同 key 追加到末尾", () => {
    const ts = pushTab(pushTab([], t("/a")), t("/b"));
    expect(ts.map((x) => x.key)).toEqual(["/a", "/b"]);
  });
});

describe("closeTabIn", () => {
  it("关当前标签退到剩下的最后一个", () => {
    const r = closeTabIn([t("/a"), t("/b")], "/b", "/b");
    expect(r.active).toBe("/a");
  });

  it("关最后一个标签后 active 归空", () => {
    const r = closeTabIn([t("/a")], "/a", "/a");
    expect(r.tabs).toHaveLength(0);
    expect(r.active).toBeNull();
  });

  it("关非当前标签不动 active", () => {
    const r = closeTabIn([t("/a"), t("/b")], "/a", "/b");
    expect(r.active).toBe("/b");
  });
});

describe("patchTabIn", () => {
  it("只改目标标签", () => {
    const ts = patchTabIn([t("/a"), t("/b")], "/b", { title: "B2" });
    expect(ts[0].title).toBe("/a");
    expect(ts[1].title).toBe("B2");
  });
});

describe("normalizeUrl", () => {
  it("空串返回 null（不弹空标签）", () => {
    expect(normalizeUrl("   ")).toBeNull();
  });

  it("缺协议补 https", () => {
    expect(normalizeUrl("example.com/x")).toBe("https://example.com/x");
  });

  it("已有协议保持不变", () => {
    expect(normalizeUrl("http://a.cn")).toBe("http://a.cn");
    expect(normalizeUrl("https://a.cn")).toBe("https://a.cn");
  });
});

describe("urlTab", () => {
  it("标题去协议且截断 24 字", () => {
    const tab = urlTab("https://example.com/" + "x".repeat(50));
    expect(tab.title.length).toBe(24);
    expect(tab.title.startsWith("example.com")).toBe(true);
    expect(tab.kind).toBe("web");
    expect(tab.key).toBe("https://example.com/" + "x".repeat(50));
  });
});
