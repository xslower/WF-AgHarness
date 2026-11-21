
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { api } from "../../kernel/api";
import { ChatController } from "../../kernel/ui/chat/chatController";
import { streamStore, resetStreamStoreForTest } from "../../kernel/ui/chat/sessionStore";
import { readInput, saveInput, markInputSent } from "../../kernel/ui/chat/chatStorage";
import { installFakeStorage } from "../../test-utils/fakeStorage";
import { startHarness, wireFakeModel, type Harness } from "./harnessServer";

let h: Harness;
let fport = 0;


async function until(fn: () => boolean | Promise<boolean>, timeoutMs = 15_000): Promise<void> {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if (await fn()) return;
    await new Promise((r) => setTimeout(r, 50));
  }
  throw new Error(`${timeoutMs}ms 内条件未成立`);
}

describe("聊天主流程 · 真后端真链路", () => {
  beforeAll(async () => {
    h = await startHarness();
    
    fport = h.fport;
    await wireFakeModel(fport);
  }, 120_000);

  afterAll(async () => { await h?.close(); });

  beforeEach(() => {
    h.bindFetch();   
    installFakeStorage();
    resetStreamStoreForTest();
  });

  
  function newCtl(): ChatController {
    const wsBase = h.baseUrl.replace(/^http/, "ws");
    return new ChatController({
      wsUrl: (sid) => `${wsBase}/ws/${sid}`,
    });
  }

  it("新建会话 → 发消息 → 真模型回复 → 真落库（user+assistant 顺序与内容）", async () => {
    const ctl = newCtl();
    let sid = "";
    const ctx = () => ({ sid, project: h.project, model: "parent",
                         onSessionCreated: (id: string) => { sid = id; } });

    
    saveInput(null, "你好，请回答");
    const ok = await ctl.send(ctx(), "你好，请回答");
    expect(ok).toBe(true);
    expect(sid).toBeTruthy();

    
    await until(() => streamStore.get(sid).messages.some(
      (m) => m.role === "assistant" && String(m.content).includes("假模型")));

    
    const s = await api.getSession(sid);
    expect(s.messages.map((m) => m.role)).toEqual(["user", "assistant"]);
    expect(s.messages[0].content).toBe("你好，请回答");
    expect(s.messages[1].content).toBe("假模型回复");

    
    expect(h.upstream.some((u) => u.body?.messages !== undefined)).toBe(true);

    
    const local = streamStore.get(sid).messages;
    expect(local.map((m) => m.role)).toEqual(["user", "assistant"]);
    expect(local).toHaveLength(2);

    
    expect(readInput(sid)).toBe("");
  }, 60_000);

  it("打字 → 发送 → 切到另一会话 → 切回 → 输入框为空（本次漏掉的那条）", async () => {
    const ctl = newCtl();
    let sid = "";
    const ctx = () => ({ sid, project: h.project, model: "parent",
                         onSessionCreated: (id: string) => { sid = id; } });

    
    saveInput(null, "这条发出去后不该再出现");
    expect(readInput(null)).toBe("这条发出去后不该再出现");

    await ctl.send(ctx(), "这条发出去后不该再出现");
    expect(sid).toBeTruthy();
    
    expect(readInput(sid)).toBe("");

    
    
    const other = await api.createSession("另一条", h.project);
    ctl.setFocus(other.id);
    ctl.setFocus(sid);
    expect(readInput(sid)).toBe("");

    
    
    await until(async () => {
      const s = await api.getSession(sid);
      return s.messages.some((m) => m.role === "assistant");
    }, 30_000);
    expect(readInput(sid)).toBe("");
  }, 60_000);

  it("回复中插队发第二条 → 两条都落库、顺序不颠倒、不重复", async () => {
    const ctl = newCtl();
    let sid = "";
    const ctx = () => ({ sid, project: h.project, model: "parent",
                         onSessionCreated: (id: string) => { sid = id; } });

    h.replyWith("第一轮回复");
    const first = await ctl.send(ctx(), "第一条");
    expect(first).toBe(true);
    
    h.replyWith("第二轮回复");
    const second = await ctl.send(ctx(), "第二条");
    expect(second).toBe(true);

    await until(async () => {
      const s = await api.getSession(sid);
      return s.messages.filter((m) => m.role === "user").length === 2
             && s.messages.filter((m) => m.role === "assistant").length === 2;
    }, 30_000);
    const s = await api.getSession(sid);
    const users = s.messages.filter((m) => m.role === "user").map((m) => m.content);
    expect(users).toEqual(["第一条", "第二条"]);
    
    const localUsers = streamStore.get(sid).messages
      .filter((m) => m.role === "user").map((m) => m.content);
    expect(new Set(localUsers).size).toBe(localUsers.length);
  }, 60_000);

  it("重启后端 → 会话与消息仍在（真落库，不是内存）", async () => {
    const ctl = newCtl();
    const sid = (await api.createSession("重启前", h.project)).id;
    const ok = await ctl.send({ sid, project: h.project, model: "parent" }, "重启前的话");
    expect(ok).toBe(true);
    await until(() => streamStore.get(sid).messages.some((m) => m.role === "assistant"));

    await h.restart();
    const s = await api.getSession(sid);
    expect(s.messages.map((m) => m.role)).toContain("user");
    expect(s.messages.map((m) => m.role)).toContain("assistant");
  }, 120_000);

  it("发送失败（后端不可达）→ 内容留在草稿、标已发送状态不提前清", async () => {
    
    const ctl = new ChatController({
      wsUrl: () => "ws://127.0.0.1:1/ws/never",
      wsFactory: () => { throw new Error("连不上"); },
    });
    const sid = (await api.createSession("失败路径", h.project)).id;
    saveInput(sid, "别把我弄丢");
    
    const ok = await ctl.send({ sid, project: h.project, model: "parent" }, "别把我弄丢");
    expect(ok).toBe(false);
    expect(readInput(sid)).toBe("别把我弄丢");

    
    expect(readInput(sid)).toBe("别把我弄丢");
    markInputSent(sid, "别把我弄丢");
    expect(readInput(sid)).toBe("");

  }, 60_000);
});
