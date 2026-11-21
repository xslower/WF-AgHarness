
import { describe, expect, it } from "vitest";
import { pickSessionId } from "./pickSessionId";

describe("pickSessionId", () => {
  it("本地记的那条还在列表里 → 保留（切页面回来看到原来那条）", () => {
    expect(pickSessionId("s1", ["s1", "s2"], "s2")).toBe("s1");
  });

  it("本地记的失效（被删/换浏览器）→ 用后端 bind 的建议", () => {
    expect(pickSessionId("gone", ["s1", "s2"], "s2")).toBe("s2");
  });

  it("本地为空 → 用 bind 结果", () => {
    expect(pickSessionId(null, ["s1"], "s1")).toBe("s1");
  });

  it("都没有 → null（宁可空，也不能沿用上一条工作流的会话）", () => {
    expect(pickSessionId(null, [], null)).toBeNull();
    expect(pickSessionId("gone", [], null)).toBeNull();
  });

  it("切到没有会话的新工作流：本地是 A 的 id、列表空 → 不能把 A 的会话带过去", () => {
    expect(pickSessionId("a-sess", [], null)).toBeNull();
  });
});
