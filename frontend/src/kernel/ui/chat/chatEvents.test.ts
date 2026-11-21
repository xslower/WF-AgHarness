import { describe, expect, it } from "vitest";
import {
  applyWsEvent, appendLive, initialStreamState, withLastAssistantMeta,
  type SessionStreamState,
} from "./chatEvents";
import { clearRoundTransients, pushNotice } from "./reducers";
import type { ChatMessage } from "../../api";


function run(events: { type?: string; [k: string]: unknown }[],
             init: SessionStreamState = initialStreamState()) {
  return events.reduce((s, e) => applyWsEvent(s, e), init);
}

describe("流式文本", () => {
  it("同 kind 连续分片合并成一条，换 kind 另起", () => {
    const live = appendLive(appendLive([], "text", "a"), "text", "b");
    expect(live).toEqual([{ kind: "text", text: "ab" }]);
    expect(appendLive(live, "reason", "思考")).toEqual([
      { kind: "text", text: "ab" },
      { kind: "reason", text: "思考" },
    ]);
  });

  it("text/reason 事件交替出现时不会粘成一条", () => {
    const s = run([
      { type: "text", text: "答" },
      { type: "reason", text: "想" },
      { type: "text", text: "案" },
    ]);
    expect(s.live).toEqual([
      { kind: "text", text: "答" },
      { kind: "reason", text: "想" },
      { kind: "text", text: "案" },
    ]);
  });

  it("不修改传入的 state（纯函数）", () => {
    const before = initialStreamState();
    const after = applyWsEvent(before, { type: "text", text: "x" });
    expect(before.live).toEqual([]);
    expect(after.live).toHaveLength(1);
    expect(after).not.toBe(before);
  });
});


describe("notice 生命周期（修「提醒全堆在最后」）", () => {
  const note = (text: string, tag?: "reconnect") =>
    ({ kind: "notice" as const, text, ...(tag ? { tag } : {}) });

  it("连接状态类就地替换：4 条重连提示只留最后一条", () => {
    let live = [] as ReturnType<typeof pushNotice>;
    for (const n of ["断1", "断2", "断3", "断4"]) {
      live = pushNotice(live, note(n, "reconnect"));
    }
    live = pushNotice(live, note("✓ 连接已恢复", "reconnect"));
    expect(live).toEqual([note("✓ 连接已恢复", "reconnect")]);
  });

  it("普通 notice 仍按序追加（同一轮里多条都要看见）", () => {
    const live = pushNotice(pushNotice([], note("已插队")), note("本轮已中止"));
    expect(live.map((e) => e.text)).toEqual(["已插队", "本轮已中止"]);
  });

  it("轮次边界收走上一轮的 notice 与 error、保留正文", () => {
    const live = [note("已插队"), { kind: "error" as const, text: "后端 500" },
      { kind: "text" as const, text: "正文" }];
    expect(clearRoundTransients(live).map((e) => e.kind)).toEqual(["text"]);
  });

  it("turn_start 开新一轮清掉上一轮的 notice 和残留 error", () => {
    const s = run([{ type: "notice", text: "上一轮的提示" },
      { type: "error", text: "RuntimeError: 子队列全部失败" },
      { type: "turn_start", id: "q2", content: "下一轮" }]);
    expect(s.live.some((e) => e.kind === "notice")).toBe(false);
    expect(s.live.some((e) => e.kind === "error")).toBe(false);  
    expect(s.busy).toBe(true);
  });

  it("done 收尾也清掉本轮 notice，但 error 保留", () => {
    const s = run([{ type: "notice", text: "已插队" }, { type: "error", text: "网关 500" },
      { type: "done" }]);
    expect(s.live.some((e) => e.kind === "notice")).toBe(false);
    expect(s.live.some((e) => e.kind === "error")).toBe(true);
  });

  it("本轮报错 done 后仍可见、发下一条才清（修闪退与残留两不误）", () => {
    const s1 = run([{ type: "error", text: "网关 500" }, { type: "done" }]);
    expect(s1.live.some((e) => e.kind === "error")).toBe(true);   
    const s2 = applyWsEvent(s1, { type: "turn_start", id: "q", content: "下一条" });
    expect(s2.live.some((e) => e.kind === "error")).toBe(false);  
  });
});

describe("工具块", () => {
  it("tool_output 只追加到最近一个还没结果的工具块", () => {
    const s = run([
      { type: "tool_start", name: "run_command" },
      { type: "tool_output", text: "第一行\n" },
      { type: "tool_output", text: "第二行\n" },
    ]);
    expect(s.live).toHaveLength(1);
    expect(s.live[0]).toMatchObject({ kind: "tool", toolName: "run_command", output: "第一行\n第二行\n" });
  });

  it("输出超过 20000 字只留尾巴", () => {
    const s = run([
      { type: "tool_start", name: "run_command" },
      { type: "tool_output", text: "x".repeat(25000) },
    ]);
    expect((s.live[0].output || "").length).toBe(20000);
  });

  it("tool_output 在没有工具块时是空操作", () => {
    const s = run([{ type: "tool_output", text: "孤立的输出" }]);
    expect(s.live).toEqual([]);
  });

  it("tool_end 按名字回填，不会填错到同名的已结束块", () => {
    const s = run([
      { type: "tool_start", name: "fs_read" },
      { type: "tool_end", name: "fs_read", args: { p: 1 }, result: "A" },
      { type: "tool_start", name: "fs_read" },
      { type: "tool_end", name: "fs_read", args: { p: 2 }, result: "B" },
    ]);
    expect(s.live.map((x) => x.result)).toEqual(["A", "B"]);
    expect(s.live[1].args).toEqual({ p: 2 });
  });

  it("subagent(action=spawn) 的结果回填到最后一个 running 卡片", () => {
    const s = run([
      { type: "subagent_start", subagent_id: "sa1", task: "跑测试" },
      { type: "tool_start", name: "subagent" },
      { type: "tool_end", name: "subagent", args: JSON.stringify({ action: "spawn" }), result: "全部通过" },
    ]);
    expect(s.subAgents.sa1.status).toBe("done");
    expect(s.subAgents.sa1.result).toBe("全部通过");
  });

  it("subagent(action=get) 不动卡片状态", () => {
    const s = run([
      { type: "subagent_start", subagent_id: "sa1", task: "跑测试" },
      { type: "tool_start", name: "subagent" },
      { type: "tool_end", name: "subagent", args: JSON.stringify({ action: "get" }), result: "running" },
    ]);
    expect(s.subAgents.sa1.status).toBe("running");
  });

  it("结果含 error 判为失败，空结果也判失败", () => {
    const failed = run([
      { type: "subagent_start", subagent_id: "a", task: "t" },
      { type: "tool_end", name: "subagent", args: '{"action":"spawn"}', result: '{"error":"boom"}' },
    ]);
    expect(failed.subAgents.a.status).toBe("failed");

    const empty = run([
      { type: "subagent_start", subagent_id: "a", task: "t" },
      { type: "tool_end", name: "subagent", args: '{"action":"spawn"}', result: "" },
    ]);
    expect(empty.subAgents.a.status).toBe("failed");
  });

  it("子 Agent 事件序列按 200 条截断", () => {
    let s = run([{ type: "subagent_start", subagent_id: "a", task: "t" }]);
    for (let i = 0; i < 250; i++) {
      s = applyWsEvent(s, { type: "subagent_event", subagent_id: "a", event: { type: "notice", text: String(i) } });
    }
    expect(s.subAgents.a.events).toHaveLength(200);
    expect(s.subAgents.a.events?.[199]).toEqual({ type: "notice", text: "249" });
  });
});

describe("轮次生命周期", () => {
  it("turn_start 置 busy 并清上一轮 notice，但不碰 messages", () => {
    const s = run([{ type: "notice", text: "上一轮提示" },
      { type: "turn_start", id: "q1", content: "你好" }],
      { ...initialStreamState(), messages: [{ role: "user", content: "你好" } as ChatMessage] });
    expect(s.busy).toBe(true);
    expect(s.messages).toEqual([{ role: "user", content: "你好" }]);
    expect(s.live.some((e) => e.kind === "notice")).toBe(false);
  });
  it("turn_start 把已开跑的那条从队列里摘掉（队列快照可能晚到/丢失）", () => {
    const s = run([{ type: "turn_start", id: "q2", from_queue: true, content: "排队的话" }], {
      ...initialStreamState(),
      queue: [
        { id: "q2", content: "排队的话", images: 0, attachments: [], workflow: "", interjecting: false },
        { id: "q3", content: "后面那条", images: 0, attachments: [], workflow: "", interjecting: false },
      ],
    });
    expect(s.queue.map((q) => q.id)).toEqual(["q3"]);
  });

  it("ctx_estimate 让用量指示器立刻回落，done 的真实 usage 再覆盖", () => {
    const base = { ...initialStreamState(),
                   ctxState: { used: 444_097, model: "glm", estimated: false } };
    const s = run([{ type: "ctx_estimate", used: 12_345 }], base);
    
    expect(s.ctxState).toEqual({ used: 12_345, model: "glm", estimated: true });
    
    expect(run([{ type: "ctx_estimate", used: -1 }], base).ctxState).toEqual(base.ctxState);
    expect(run([{ type: "ctx_estimate" }], base).ctxState).toEqual(base.ctxState);
  });

  it("工具轮 ctx_estimate：带 model、数值会涨，且 0 不写成 0 占用", () => {
    const init = { ...initialStreamState(),
      ctxState: { used: 100, model: "glm", estimated: true } };
    
    const mid = run([{ type: "ctx_estimate", used: 4321, model: "p/m", estimated: true }], init);
    expect(mid.ctxState).toEqual({ used: 4321, model: "p/m", estimated: true });
    
    expect(run([{ type: "ctx_estimate", used: 0 }], mid).ctxState).toEqual(mid.ctxState);
  });

  it("done 带全 0 usage 壳时保留上一份可信占用（不出现 0 占用）", () => {
    const init = { ...initialStreamState(),
      ctxState: { used: 8000, model: "p/m", estimated: true } };
    const s = run([{ type: "done", model: "p/m",
      usage: { prompt_tokens: 0, completion_tokens: 0 } }], init);
    expect(s.ctxState).toEqual(init.ctxState);
  });

  it("done 记下上游真实 usage（estimated=false）", () => {
    const s = run([{ type: "text", text: "好的" },
      { type: "done", model: "deepseek/chat", usage: { prompt_tokens: 100, completion_tokens: 20 } }],
      { ...initialStreamState(),
        messages: [{ role: "user", content: "问" } as ChatMessage] });
    expect(s.busy).toBe(false);
    expect(s.ctxState).toEqual({ used: 120, model: "deepseek/chat", estimated: false });
  });
  it("队列里还有消息时 done 之后仍然 busy（按钮不闪回空闲）", () => {
    const s = run([
      { type: "queue", items: [{ id: "1", text: "下一条" }] },
      { type: "done" },
    ]);
    expect(s.busy).toBe(true);
  });

  it("error 停下本轮并留一条错误", () => {
    const s = run([{ type: "turn_start", id: "q" }, { type: "error", text: "网关 500" }]);
    expect(s.busy).toBe(false);
    expect(s.stopping).toBe(false);
    expect(s.live.at(-1)).toEqual({ kind: "error", text: "网关 500" });
  });

  it("没有 assistant 消息时 done 不炸", () => {
    const s = run([{ type: "done", ts: 1, cost: 0 }]);
    expect(s.messages).toEqual([]);
  });
});

describe("计划模式与其它状态", () => {
  it("计划状态按事件流转", () => {
    let s = run([{ type: "plan_start" }]);
    expect(s.planState.status).toBe("planning");
    s = applyWsEvent(s, { type: "plan_ready", text: "第一步…" });
    expect(s.planState).toEqual({ status: "awaiting_approval", planText: "第一步…" });
    s = applyWsEvent(s, { type: "plan_approved" });
    expect(s.planState.status).toBe("executing");
    s = applyWsEvent(s, { type: "plan_cancelled" });
    expect(s.planState.status).toBe("idle");
  });

  it("审批请求进来、处理完移除", () => {
    let s = run([{ type: "approval_request", id: "ap1", tool: "run_command" }]);
    expect(s.pendingApprovals).toHaveLength(1);
    s = applyWsEvent(s, { type: "approval_done", id: "ap1" });
    expect(s.pendingApprovals).toHaveLength(0);
  });

  it("todo / suggestions 收到非数组就清空，不保留脏值", () => {
    const s = run([
      { type: "todo", todos: [{ id: "1", text: "a", status: "pending" }] },
      { type: "todo", todos: null },
      { type: "suggestions", items: ["继续"] },
      { type: "suggestions", items: "坏数据" },
    ]);
    expect(s.todos).toEqual([]);
    expect(s.suggestions).toEqual([]);
  });

  it("未知事件返回原引用（调用方可据此跳过渲染）", () => {
    const before = initialStreamState();
    expect(applyWsEvent(before, { type: "未来才有的事件" })).toBe(before);
    expect(applyWsEvent(before, {})).toBe(before);
  });

  it("withLastAssistantMeta 找不到 assistant 时原样返回", () => {
    const msgs: ChatMessage[] = [{ role: "user", content: "hi" } as ChatMessage];
    expect(withLastAssistantMeta(msgs, { ts: 1 })).toBe(msgs);
  });
});



describe("轮次事件不碰 messages", () => {
  const history = [
    { role: "user", content: "第一条" },
    { role: "assistant", content: "上一条回复" },
    { role: "user", content: "中途插的话" },
  ] as ChatMessage[];

  it("turn_start 只切 busy/notice，不补插用户气泡", () => {
    const s = run([{ type: "turn_start", id: "q9", content: "你好" }],
      { ...initialStreamState(), messages: history });
    expect(s.busy).toBe(true);
    expect(s.messages).toEqual(history);
  });

  it("断线重放同一条 turn_start 多次，messages 一条不变", () => {
    const ev = { type: "turn_start", id: "q9", from_queue: true, content: "中途插的话" };
    const s = run([ev, ev, ev], { ...initialStreamState(), messages: history });
    expect(s.messages).toEqual(history);
  });

  it("done 不动 messages（本轮正文还在 live，等 turn_saved 落库再覆盖）", () => {
    const s = run([{ type: "text", text: "本轮回复" }, { type: "done" }],
      { ...initialStreamState(), messages: history, busy: true });
    expect(s.messages).toEqual(history);
    expect(s.live.some((e) => e.kind === "text")).toBe(true);
    expect(s.busy).toBe(false);
  });

  it("error 也不动 messages（本地已插入的气泡等账本覆盖）", () => {
    const s = run([{ type: "error", text: "网关 500" }],
      { ...initialStreamState(), messages: history, busy: true });
    expect(s.messages).toEqual(history);
    expect(s.busy).toBe(false);
    expect(s.live.at(-1)).toMatchObject({ kind: "error", text: "网关 500" });
  });

  it("resume 轮同样不补插（后端落库的是 _sys=resume 提示条）", () => {
    const s = run([{ type: "turn_start", id: "", resume: true, content: "原计划文本" }],
      { ...initialStreamState(), messages: history });
    expect(s.messages).toEqual(history);
    expect(s.busy).toBe(true);
  });

  it("queue 项按 id 从面板摘掉，但 messages 不动", () => {
    const s = run([{ type: "turn_start", id: "q2", from_queue: true, content: "排队的话" }],
      { ...initialStreamState(), messages: history,
        queue: [{ id: "q2", content: "排队的话", images: 0, attachments: [], workflow: "", interjecting: false }] });
    expect(s.queue).toHaveLength(0);
    expect(s.messages).toEqual(history);
  });
});
