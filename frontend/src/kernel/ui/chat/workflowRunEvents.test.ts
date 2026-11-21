
import { describe, expect, it } from "vitest";
import { applyWsEvent, initialStreamState, type SessionStreamState } from "./chatEvents";

function run(events: { type?: string; [k: string]: unknown }[],
             init: SessionStreamState = initialStreamState()) {
  return events.reduce((s, e) => applyWsEvent(s, e), init);
}

describe("workflow_run", () => {
  it("run_id 挂到最近的 workflow 工具块上", () => {
    const s = run([
      { type: "tool_start", name: "workflow", args: { action: "run", name: "研报" } },
      { type: "workflow_run", phase: "start", run_id: "r1", workflow: "研报" },
    ]);
    expect(s.live).toHaveLength(1);
    expect(s.live[0]).toMatchObject({ kind: "tool", toolName: "workflow", wfRunId: "r1" });
  });

  it("没有 run_id 的事件不改变状态（不新增空块）", () => {
    const base = run([{ type: "tool_start", name: "workflow", args: {} }]);
    const after = applyWsEvent(base, { type: "workflow_run", phase: "start" });
    expect(after).toBe(base);
  });

  it("不误挂到别的工具块上", () => {
    const s = run([
      { type: "tool_start", name: "f_read", args: {} },
      { type: "workflow_run", run_id: "r1" },
    ]);
    expect(s.live[0].wfRunId).toBeUndefined();
  });

  it("节点进度按 tool_output 累积到同一个工具块", () => {
    const s = run([
      { type: "tool_start", name: "workflow", args: {} },
      { type: "workflow_run", run_id: "r1" },
      { type: "tool_output", name: "workflow", text: "▶ s1 · 运行中\n" },
      { type: "tool_output", name: "workflow", text: "✓ s1 · 完成（12ms）\n" },
    ]);
    expect(s.live).toHaveLength(1);
    expect(s.live[0].output).toBe("▶ s1 · 运行中\n✓ s1 · 完成（12ms）\n");
  });

  it("tool_end 之后仍保留 run id（结果回来入口还在）", () => {
    const s = run([
      { type: "tool_start", name: "workflow", args: {} },
      { type: "workflow_run", run_id: "r1" },
      { type: "tool_end", name: "workflow", args: {}, result: "done\n\n[run_id:r1]" },
    ]);
    expect(s.live[0]).toMatchObject({ wfRunId: "r1", result: "done\n\n[run_id:r1]" });
  });
});
