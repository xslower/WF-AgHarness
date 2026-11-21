
import { afterEach, describe, expect, it } from "vitest";
import { bindSubAgentOpener, openSubAgentTab, type SubAgentOpenRequest } from "./subAgentTab";

afterEach(() => bindSubAgentOpener(null));

describe("openSubAgentTab", () => {
  it("没绑定 opener 时调用不抛（面板未打开的场景）", () => {
    expect(() => openSubAgentTab({ id: "sa_1", task: "调研" })).not.toThrow();
  });

  it("绑定后把请求原样交给 opener", () => {
    const got: SubAgentOpenRequest[] = [];
    bindSubAgentOpener((r) => got.push(r));
    openSubAgentTab({ id: "sa_1", task: "调研", sessionId: "s1" });
    expect(got).toEqual([{ id: "sa_1", task: "调研", sessionId: "s1" }]);
  });

  it("解绑后不再触发（面板卸载）", () => {
    const got: SubAgentOpenRequest[] = [];
    bindSubAgentOpener((r) => got.push(r));
    bindSubAgentOpener(null);
    openSubAgentTab({ id: "sa_1", task: "调研" });
    expect(got).toEqual([]);
  });
});
