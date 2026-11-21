
import { beforeEach, describe, expect, it } from "vitest";
import {
  clearAttentionFocus, getAttentionFocus, resetAttentionFocusForTest,
  setAttentionFocus, subscribeAttentionFocus,
} from "./focus";

beforeEach(() => { resetAttentionFocusForTest(); });

describe("attention focus 登记", () => {
  it("设置后能被读到，并通知订阅者", () => {
    let hits = 0;
    const off = subscribeAttentionFocus(() => { hits += 1; });
    setAttentionFocus("s1");
    expect(getAttentionFocus()).toBe("s1");
    expect(hits).toBe(1);
    off();
  });

  it("设成同一个值不重复通知（避免每轮渲染都刷新侧栏）", () => {
    setAttentionFocus("s1");
    let hits = 0;
    const off = subscribeAttentionFocus(() => { hits += 1; });
    setAttentionFocus("s1");
    expect(hits).toBe(0);
    setAttentionFocus("s2");
    expect(hits).toBe(1);
    off();
  });

  it("只有自己登记的那条能清（别把别处的焦点误清）", () => {
    setAttentionFocus("s2");
    clearAttentionFocus("s1");       
    expect(getAttentionFocus()).toBe("s2");
    clearAttentionFocus("s2");
    expect(getAttentionFocus()).toBeNull();
  });

  it("空值等同没有焦点", () => {
    setAttentionFocus("");
    expect(getAttentionFocus()).toBeNull();
  });
});
