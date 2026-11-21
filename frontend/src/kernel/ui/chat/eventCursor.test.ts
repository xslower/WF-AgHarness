
import { describe, expect, it } from "vitest";
import { EventCursors, pendingReplay } from "./eventCursor";

describe("事件游标", () => {
  it("只进不退：更大的序号才推进", () => {
    const c = new EventCursors();
    c.advance("s1", 10);
    c.advance("s1", 5);      
    expect(c.get("s1")).toBe(10);
    c.advance("s1", 11);
    expect(c.get("s1")).toBe(11);
  });

  it("没有序号的旧事件被忽略", () => {
    const c = new EventCursors();
    c.track("s1", { type: "text" });
    c.track("s1", { type: "text", _i: 0 });
    expect(c.get("s1")).toBe(0);
  });

  it("不同会话各记各的", () => {
    const c = new EventCursors();
    c.advance("a", 3);
    c.advance("b", 7);
    expect(c.get("a")).toBe(3);
    expect(c.get("b")).toBe(7);
  });
});

describe("重放过滤（幂等）", () => {
  it("只给还没应用过的事件", () => {
    const c = new EventCursors();
    c.advance("s1", 5);
    const items = [
      { i: 4, e: { type: "text" } },
      { i: 5, e: { type: "text" } },
      { i: 6, e: { type: "text" } },
      { i: 7, e: { type: "text" } },
    ];
    const out = pendingReplay(items, c, "s1");
    expect(out.map((e) => e._i)).toEqual([6, 7]);
  });

  it("过滤后游标推进到最后一条", () => {
    const c = new EventCursors();
    pendingReplay([{ i: 3, e: {} }, { i: 9, e: {} }], c, "s1");
    expect(c.get("s1")).toBe(9);
  });

  it("没有重放内容时不动游标", () => {
    const c = new EventCursors();
    c.advance("s1", 4);
    expect(pendingReplay(undefined, c, "s1")).toEqual([]);
    expect(pendingReplay([], c, "s1")).toEqual([]);
    expect(c.get("s1")).toBe(4);
  });

  it("坏数据（没有 i / 不是对象）被跳过", () => {
    const c = new EventCursors();
    const out = pendingReplay(
      [{ i: 0, e: { type: "text" } }, { i: 2, e: null as never }, { i: 3, e: { type: "text" } }],
      c, "s1",
    );
    expect(out.map((e) => e._i)).toEqual([3]);
  });

  
  it("瞬时过程事件重放时不重新显示，但游标照样推进", () => {
    const c = new EventCursors();
    c.advance("s1", 10);
    const items = [
      { i: 11, e: { type: "notice", text: "连接中断…" } },
      { i: 12, e: { type: "queued", text: "已插队" } },
      { i: 13, e: { type: "queue_full", text: "队列已满" } },
      { i: 14, e: { type: "text", text: "真正要补的内容" } },
      { i: 15, e: { type: "notice", text: "▶ 发送排队消息" } },
    ];
    const out = pendingReplay(items, c, "s1");
    expect(out.map((e) => e.type)).toEqual(["text"]);
    expect(out[0].text).toBe("真正要补的内容");
    expect(c.get("s1")).toBe(15);   
    expect(pendingReplay(items, c, "s1")).toEqual([]);
  });
});
