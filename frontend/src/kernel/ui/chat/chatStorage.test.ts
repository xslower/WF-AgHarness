import { beforeEach, describe, expect, it } from "vitest";
import {
  clearPartial, clearSentInput, historyOf, lastCtxState, markInputSent,
  readInput, readPartial, saveInput, savePartial, usageFromDetail,
} from "./chatStorage";
import type { ChatMessage } from "../../api";
import { installFakeStorage } from "../../../test-utils/fakeStorage";
import { dropSession } from "../../chat/chatSessionStore";


beforeEach(() => { installFakeStorage(); });

describe("输入框草稿（唯一一份，带 sent 状态）", () => {
  it("打字随改随记、按 sid 隔离、切回来不串", () => {
    saveInput("a", "在 A 打了一半");
    saveInput("b", "B 的内容");
    expect(readInput("a")).toBe("在 A 打了一半");
    expect(readInput("b")).toBe("B 的内容");
    expect(readInput("c")).toBe("");
  });

  it("发出后不再回填（2026-11-09 修「发完切会话又冒出来」）", () => {
    saveInput("a", "要发出去的话");
    markInputSent("a", "要发出去的话");
    expect(readInput("a")).toBe("");
    
    saveInput("a", "");
    expect(readInput("a")).toBe("");
  });

  it("后端确认入库后清除；只清已发送那份", () => {
    saveInput("a", "已发送");
    markInputSent("a", "已发送");
    clearSentInput("a");
    expect(readInput("a")).toBe("");
    expect(readInput("a")).toBe("");
    expect(JSON.parse(localStorage.getItem("chat.a")!)).toEqual({});
  });

  it("回复期间重新打字（未发送）不会被确认入库误清", () => {
    saveInput("a", "已发送");
    markInputSent("a", "已发送");
    saveInput("a", "新打的一半");
    clearSentInput("a");
    expect(readInput("a")).toBe("新打的一半");
  });

  it("空串删除未发送草稿，不留空壳；发送失败时草稿还在", () => {
    saveInput("a", "x");
    saveInput("a", "");
    expect(readInput("a")).toBe("");
    expect(JSON.parse(localStorage.getItem("chat.a")!)).toEqual({});
    saveInput("a", "没发出去的");
    expect(readInput("a")).toBe("没发出去的");   
  });

  it("sid 为 null 走「新建槽位」，不会串到已有会话", () => {
    saveInput(null, "还没建会话时写的");
    saveInput("a", "A");
    expect(readInput(null)).toBe("还没建会话时写的");
    expect(readInput("a")).toBe("A");
  });

  it("每条会话一个键，互不设全局上限", () => {
    for (let i = 0; i < 80; i++) saveInput(`s${i}`, `内容${i}`);
    expect(readInput("s79")).toBe("内容79");
    expect(readInput("s0")).toBe("内容0");
    dropSession("s0");
    expect(readInput("s0")).toBe("");
  });

  it("坏数据读回空串，不抛", () => {
    localStorage.setItem("chat.a", "{oops");
    expect(readInput("a")).toBe("");
  });

  it("配额不足时静默失败（不能因为存草稿把交互炸掉）", () => {
    installFakeStorage(true);
    expect(() => saveInput("a", "x")).not.toThrow();
    expect(readInput("a")).toBe("");
  });
});

describe("流式快照", () => {
  it("落盘带时间戳，读回三个字段", () => {
    savePartial("s1", { text: "半截", reason: "想", ts: 123 });
    expect(readPartial("s1")).toEqual({ text: "半截", reason: "想", ts: 123 });
  });

  it("结构不对（没有 text）当没存过", () => {
    const map = installFakeStorage();
    map.set("chat.s1", JSON.stringify({ partial: { reason: "只有思考" } }));
    expect(readPartial("s1")).toBeNull();
  });

  it("清除后读回 null", () => {
    savePartial("s1", { text: "t", reason: "", ts: 1 });
    clearPartial("s1");
    expect(readPartial("s1")).toBeNull();
  });

  it("配额满清不掉盘上快照时，内存墓碑仍让本次页面不误报", () => {
    const map = installFakeStorage();
    savePartial("s1", { text: "半截", reason: "", ts: 1 });
    expect(readPartial("s1")).not.toBeNull();
    (globalThis as any).localStorage.setItem = () => { throw new Error("QuotaExceededError"); };
    expect(() => clearPartial("s1")).not.toThrow();
    expect(map.get("chat.s1")).toContain("半截");
    expect(readPartial("s1")).toBeNull();
  });
});

describe("历史摘要", () => {
  const msgs = [
    { role: "user", content: "第一个问题" },
    { role: "assistant", content: "答一", model: "m1", usage: { prompt_tokens: 3, completion_tokens: 5 } },
    { role: "user", content: "第二个问题" },
    {
      role: "assistant", content: "", model: "m2", reasoning: "想想",
      tool_calls: [{ function: { name: "read_file", arguments: "{\"path\":\"a\"}" } }],
    },
  ] as unknown as ChatMessage[];

  it("按 user 消息分轮，request/response 交替", () => {
    const h = historyOf(msgs);
    expect(h.map((x) => x.event)).toEqual([
      "request", "response", "request", "response"]);
    expect(h.map((x) => x.round)).toEqual([1, 1, 2, 2]);
  });

  it("记录工具调用与思考（没有正文的那轮也能看出在调工具）", () => {
    const last = historyOf(msgs)[3];
    expect(last.has_tool_calls).toBe(true);
    expect((last.tool_calls as any[])[0].name).toBe("read_file");
    expect(last.reasoning).toBe("想想");
  });

  it("长文本截断到 500 字，避免调试面板被撑爆", () => {
    const long = [{ role: "user", content: "字".repeat(900) }] as ChatMessage[];
    expect((historyOf(long)[0].last_user_msg as string).length).toBe(500);
  });

  it("lastCtxState 取最后一条带 usage 的消息", () => {
    expect(lastCtxState(msgs)).toEqual({ used: 8, model: "m1", estimated: false });
    expect(lastCtxState([{ role: "user", content: "x" }] as ChatMessage[])).toBeNull();
  });
});

describe("usageFromDetail（0 占用 bug 的根因：详情 usage 是唯一真源）", () => {
  it("后端估算值带上 estimated 标记，优先于消息里翻出来的旧值", () => {
    expect(usageFromDetail({ usage: { used: 12345, model: "p/m", estimated: true } }))
      .toEqual({ used: 12345, model: "p/m", estimated: true });
  });
  it("真实 usage 也照常返回", () => {
    expect(usageFromDetail({ usage: { used: 1000, model: "p/m" } }))
      .toEqual({ used: 1000, model: "p/m", estimated: false });
  });
  it("null / used=0 的空壳都不算有效值（不写 0 占用）", () => {
    expect(usageFromDetail(null)).toBeNull();
    expect(usageFromDetail({ usage: null })).toBeNull();
    expect(usageFromDetail({ usage: { used: 0, model: "p/m" } })).toBeNull();
  });
});
