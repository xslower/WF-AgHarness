
import { describe, expect, it } from "vitest";
import { mergeSubAgentEvents } from "./subAgentEvents";

describe("mergeSubAgentEvents", () => {
  it("tool_start/tool_end 结构事件不再渲染（信息已在 messages 里）", () => {
    const blocks = mergeSubAgentEvents([
      { type: "tool_start", name: "grep" },
      { type: "tool_end", name: "grep", text: "命中 3 处" },
    ]);
    expect(blocks).toEqual([]);
  });

  it("同名工具的输出聚成一块（不再每条一个 details）", () => {
    const blocks = mergeSubAgentEvents([
      { type: "tool_output", name: "run_command", text: "line1\n" },
      { type: "tool_output", name: "run_command", text: "line2\n" },
    ]);
    expect(blocks).toEqual([
      { kind: "tool", name: "run_command", text: "line1\nline2\n" },
    ]);
  });

  it("不同工具的输出各自成块", () => {
    const blocks = mergeSubAgentEvents([
      { type: "tool_output", name: "grep", text: "a" },
      { type: "tool_output", name: "f_read", text: "b" },
    ]);
    expect(blocks.map((b) => b.name)).toEqual(["grep", "f_read"]);
  });

  it("连续 text 分片合并成一段（不是一行行 token 流）", () => {
    const blocks = mergeSubAgentEvents([
      { type: "text", text: "结论" },
      { type: "text", text: "如下" },
      { type: "text", text: "。" },
    ]);
    expect(blocks).toEqual([{ kind: "text", text: "结论如下。" }]);
  });

  it("text 与 reason 交替不粘连", () => {
    const blocks = mergeSubAgentEvents([
      { type: "text", text: "答" },
      { type: "reason", text: "想" },
      { type: "text", text: "案" },
    ]);
    expect(blocks.map((b) => b.kind)).toEqual(["text", "reason", "text"]);
  });

  it("没有正文的工具块不渲染（避免光秃秃的空 details）", () => {
    const blocks = mergeSubAgentEvents([
      { type: "tool_output", name: "f_read", text: "   " },
      { type: "notice", text: "" },
    ]);
    expect(blocks).toEqual([]);
  });

  it("有正文的 notice 保留（子 Agent 的旁白要看得到）", () => {
    const blocks = mergeSubAgentEvents([
      { type: "notice", text: "⚠ 只读模式" },
    ]);
    expect(blocks).toEqual([{ kind: "text", text: "⚠ 只读模式" }]);
  });
});
