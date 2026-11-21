import { describe, expect, it } from "vitest";
import type { ChatMessage } from "../../api";
import { mergeWindow } from "./windowMerge";

const u = (t: string): ChatMessage => ({ role: "user", content: t });
const a = (t: string): ChatMessage => ({ role: "assistant", content: t });


describe("mergeWindow（落库窗口覆盖，零内容比对）", () => {
  it("服务端窗口覆盖本地对应区间，不产生第二份", () => {
    
    const local = [u("你1"), a("回复1")];
    const w = mergeWindow({ messages: local, offset: 0 },
      { messages: [u("你1"), a("回复1落库版")], offset: 0 }, false);
    expect(w.messages.map((m) => m.content)).toEqual(["你1", "回复1落库版"]);
    expect(w.messages).toHaveLength(2);
  });

  it("用户在回复途中发的话（服务端还没入库）按位置接在窗口之后", () => {
    
    const local = [u("你1"), a("回复1"), u("你2")];
    const w = mergeWindow({ messages: local, offset: 0 },
      { messages: [u("你1"), a("回复1")], offset: 0 }, false);
    expect(w.messages.map((m) => m.content)).toEqual(["你1", "回复1", "你2"]);
    expect(w.messages[2]).toBe(local[2]);
  });

  it("往上翻出来的更早历史原样保留，不被尾部窗口覆盖", () => {
    
    const head = [a("更早1"), u("更早2")];
    const local = [...head, u("你1"), a("回复1")];
    const w = mergeWindow({ messages: local, offset: 0 },
      { messages: [u("你1"), a("回复1落库版")], offset: 2 }, true);
    expect(w.messages.map((m) => m.content))
      .toEqual(["更早1", "更早2", "你1", "回复1落库版"]);
    expect(w.offset).toBe(0);
    expect(w.hasMore).toBe(true);
  });

  it("服务端窗口为空时不丢本地消息", () => {
    const local = [u("你1")];
    const w = mergeWindow({ messages: local, offset: 0 },
      { messages: [], offset: 0 }, false);
    expect(w.messages).toEqual(local);
  });

  it("服务端窗口从 0 开始、本地为空 → 直接用服务端", () => {
    const w = mergeWindow({ messages: [], offset: 0 },
      { messages: [u("你1"), a("回复1")], offset: 0 }, false);
    expect(w.messages.map((m) => m.content)).toEqual(["你1", "回复1"]);
    expect(w.offset).toBe(0);
  });

  it("用户真连发两句一样的话：窗口内两条都在，本地不新增也不删", () => {
    const same = u("同一句");
    const w = mergeWindow({ messages: [same, same], offset: 0 },
      { messages: [u("同一句"), u("同一句")], offset: 0 }, false);
    expect(w.messages).toHaveLength(2);
  });
});
