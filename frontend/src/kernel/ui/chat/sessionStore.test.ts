
import { beforeEach, describe, expect, it, vi } from "vitest";
import { initialStreamState } from "./chatEvents";
import { SessionStreamStore } from "./sessionStore";

let store: SessionStreamStore;

beforeEach(() => {
  store = new SessionStreamStore();
});

describe("会话状态按 sid 寻址", () => {
  it("未记录的会话返回共享空状态（引用稳定，避免无谓重渲染）", () => {
    const a = store.get("s1");
    const b = store.get("s1");
    expect(a).toBe(b);
    expect(a.messages).toEqual([]);
    expect(a.ctxState).toBeNull();
  });

  it("新建空会话：所有字段是初值（不能残留上一条的内容）", () => {
    store.apply("s1", { type: "text", text: "上一条的内容" });
    store.apply("s1", { type: "done", usage: { prompt_tokens: 100, completion_tokens: 20 } });
    expect(store.get("s1").ctxState).toEqual({ used: 120, model: "", estimated: false });

    
    store.replace("", initialStreamState());
    const fresh = store.get("");
    expect(fresh.messages).toEqual([]);
    expect(fresh.live).toEqual([]);
    expect(fresh.busy).toBe(false);
    expect(fresh.ctxState).toBeNull();     
    expect(fresh.todos).toEqual([]);
    expect(fresh.queue).toEqual([]);
    expect(fresh.planState).toEqual({ status: "idle", planText: "" });
  });

  it("两会话并行：一条的事件不会写进另一条", () => {
    store.apply("s1", { type: "text", text: "我是 s1" });
    store.apply("s1", { type: "tool_start", name: "read_file" });
    store.apply("s2", { type: "text", text: "我是 s2" });

    expect(store.get("s1").live.map((e) => e.text)).toEqual(["我是 s1", ""]);
    expect(store.get("s2").live.map((e) => e.text)).toEqual(["我是 s2"]);
    expect(store.get("s1").busy).toBe(false);

    store.apply("s1", { type: "turn_start" });
    expect(store.get("s1").busy).toBe(true);
    expect(store.get("s2").busy).toBe(false);  
  });

  it("上下文用量跟着会话走", () => {
    store.apply("s1", { type: "done", usage: { prompt_tokens: 900, completion_tokens: 100 } });
    expect(store.get("s1").ctxState).toEqual({ used: 1000, model: "", estimated: false });
    expect(store.get("s2").ctxState).toBeNull();

    store.patch("s2", { ctxState: { used: 5, model: "m" } });
    expect(store.get("s1").ctxState?.used).toBe(1000);
    expect(store.get("s2").ctxState?.used).toBe(5);
  });

  it("切走再切回：状态还在（不靠事件重放）", () => {
    store.apply("s1", { type: "text", text: "半截输出" });
    store.apply("s1", { type: "todo", todos: [{ id: "1", text: "做点事", done: false }] });
    store.apply("s1", { type: "queue", items: [{ id: "q1", content: "排队中" }] });

    
    store.get("s2");
    const back = store.get("s1");
    expect(back.live[0].text).toBe("半截输出");
    expect(back.todos).toHaveLength(1);
    expect(back.queue[0].content).toBe("排队中");
  });

  it("订阅只通知对应会话", () => {
    const cb1 = vi.fn();
    const cb2 = vi.fn();
    const off1 = store.subscribe("s1", cb1);
    store.subscribe("s2", cb2);

    store.apply("s1", { type: "text", text: "x" });
    expect(cb1).toHaveBeenCalledTimes(1);
    expect(cb2).not.toHaveBeenCalled();

    off1();
    store.apply("s1", { type: "text", text: "y" });
    expect(cb1).toHaveBeenCalledTimes(1);   
  });

  it("未知事件不触发通知（不做无谓渲染）", () => {
    store.ensure("s1");
    const cb = vi.fn();
    store.subscribe("s1", cb);
    expect(store.apply("s1", { type: "完全不认识的事件" })).toBe(false);
    expect(cb).not.toHaveBeenCalled();
  });

  it("删除会话：状态与订阅一起清掉", () => {
    store.apply("s1", { type: "text", text: "x" });
    const cb = vi.fn();
    store.subscribe("s1", cb);
    store.drop("s1");
    expect(store.has("s1")).toBe(false);
    expect(store.get("s1").live).toEqual([]);
    expect(store.snapshotAll().size).toBe(0);
  });

  it("patch 只覆盖指定字段，不冲掉其它会话/字段", () => {
    store.apply("s1", { type: "text", text: "保留我" });
    store.patch("s1", { busy: true });
    expect(store.get("s1").live[0].text).toBe("保留我");
    expect(store.get("s1").busy).toBe(true);
    expect(store.get("s2").busy).toBe(false);
  });
});
