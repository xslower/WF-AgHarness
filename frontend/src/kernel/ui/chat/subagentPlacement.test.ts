
import { describe, expect, it } from "vitest";
import { applyWsEvent, initialStreamState, type SessionStreamState } from "./chatEvents";

function run(events: { type?: string; [k: string]: unknown }[],
             init: SessionStreamState = initialStreamState()) {
  return events.reduce((s, e) => applyWsEvent(s, e), init);
}

const kinds = (s: SessionStreamState) => s.live.map((e) => e.kind);

describe("子 Agent 卡片就地插入", () => {
  it("卡片出现在它被创建的位置（不带去底部）", () => {
    const s = run([
      { type: "text", text: "我先派个活" },
      { type: "subagent_start", subagent_id: "sa1", task: "跑测试" },
    ]);
    expect(kinds(s)).toEqual(["text", "subagent"]);
    expect(s.live[1].subagentId).toBe("sa1");
  });

  it("后续文本排在卡片之后，顺序与发生顺序一致", () => {
    const s = run([
      { type: "subagent_start", subagent_id: "sa1", task: "跑测试" },
      { type: "text", text: "等它回来" },
    ]);
    expect(kinds(s)).toEqual(["subagent", "text"]);
  });

  it("卡片位置不随后续事件改变（工具块也不会插到它前面）", () => {
    const s = run([
      { type: "text", text: "开始" },
      { type: "subagent_start", subagent_id: "sa1", task: "跑测试" },
      { type: "tool_start", name: "f_read" },
      { type: "tool_end", name: "f_read", result: "ok" },
    ]);
    expect(kinds(s)).toEqual(["text", "subagent", "tool"]);
    expect(s.live.findIndex((e) => e.kind === "subagent")).toBe(1);
  });

  it("多个子 Agent 各自占一格，顺序按启动先后", () => {
    const s = run([
      { type: "subagent_start", subagent_id: "a", task: "任务A" },
      { type: "subagent_start", subagent_id: "b", task: "任务B" },
      { type: "subagent_start", subagent_id: "a", task: "任务A" },   
    ]);
    expect(kinds(s)).toEqual(["subagent", "subagent"]);
    expect(s.live.map((e) => e.subagentId)).toEqual(["a", "b"]);   
  });

  it("重连重放同一个 subagent_start 不会插出第二张卡", () => {
    const first = run([{ type: "subagent_start", subagent_id: "sa1", task: "t" }]);
    const again = run([{ type: "subagent_start", subagent_id: "sa1", task: "t" }], first);
    expect(kinds(again)).toEqual(["subagent"]);
    expect(again.subAgents.sa1.task).toBe("t");
  });

  it("subagent_event / _done 只更新卡片，不改位置与数量", () => {
    const s = run([
      { type: "subagent_start", subagent_id: "sa1", task: "跑测试" },
      { type: "subagent_event", subagent_id: "sa1", event: { type: "text", text: "hi" } },
      { type: "subagent_done", subagent_id: "sa1", status: "done" },
    ]);
    expect(kinds(s)).toEqual(["subagent"]);
    expect(s.subAgents.sa1.status).toBe("done");
    expect(s.subAgents.sa1.events).toHaveLength(1);
  });

  it("本轮 done 之后卡片随 live 清空（会话过去就过去了）", () => {
    const s = run([
      { type: "subagent_start", subagent_id: "sa1", task: "跑测试" },
      { type: "text", text: "结果如下" },
      { type: "done" },
    ]);
    
    expect(kinds(s).includes("subagent")).toBe(false);
  });
});
