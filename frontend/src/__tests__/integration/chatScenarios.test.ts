
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatController } from "../../kernel/ui/chat/chatController";
import { streamStore, resetStreamStoreForTest } from "../../kernel/ui/chat/sessionStore";
import { readInput, saveInput } from "../../kernel/ui/chat/chatStorage";
import { installFakeStorage } from "../../test-utils/fakeStorage";



class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 1;
  sent: Record<string, unknown>[] = [];
  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
    
    
    queueMicrotask(() => this.onopen?.());
  }
  send(raw: string) { this.sent.push(JSON.parse(raw) as Record<string, unknown>); }
  close() { this.readyState = 3; this.onclose?.({ code: 1000 }); }
  
  emit(ev: Record<string, unknown>) {
    this.onmessage?.({ data: JSON.stringify(ev) });
  }
  static last() { return FakeWebSocket.instances.at(-1)!; }
}



interface Msg { role: string; content: string }
const db = new Map<string, Msg[]>();
let seq = 0;
let realFetch: typeof fetch;

function stubBackend() {
  realFetch = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : String(input);
    const method = init?.method || "GET";
    const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : {};
    const json = (o: unknown, status = 200) => new Response(JSON.stringify(o), {
      status, headers: { "Content-Type": "application/json" },
    });
    
    if (url.startsWith("/api/sessions?") && method === "POST") {
      const id = `s${++seq}`;
      db.set(id, []);
      return json({ id });
    }
    
    const gm = /^\/api\/sessions\/([^/?]+)(?:\?|$)/.exec(url);
    if (gm && method === "GET") {
      const msgs = db.get(gm[1]) || [];
      return json({ id: gm[1], messages: msgs, offset: 0, has_more: false, todos: [] });
    }
    if (url.includes("/live")) {
      const sid = /\/api\/sessions\/([^/]+)\/live/.exec(url)![1];
      return json({ running: false, stream: [], queue: [], plan: { status: "idle" },
                    replay: [], lastSeq: 0, sid });
    }
    if (url.startsWith("/api/config")) return json({ providers: [], queues: {}, settings: {} });
    if (url.startsWith("/api/projects")) return json({ path: "/proj", name: "proj" });
    void body;
    return json({}, 404);
  }) as typeof fetch;
}


function dbAppend(sid: string, ...msgs: Msg[]) {
  const cur = db.get(sid) || [];
  cur.push(...msgs);
  db.set(sid, cur);
}

let ctl: ChatController;

function newCtl(wsFactory?: (url: string) => WebSocket) {
  return new ChatController({
    wsUrl: (sid) => `ws://test/ws/${sid}`,
    wsFactory: wsFactory ?? ((url) => new FakeWebSocket(url) as unknown as WebSocket),
  });
}

beforeEach(() => {
  installFakeStorage();
  resetStreamStoreForTest();
  db.clear();
  seq = 0;
  FakeWebSocket.instances = [];
  stubBackend();
  ctl = newCtl();
});

afterEach(() => {
  globalThis.fetch = realFetch;
  vi.restoreAllMocks();
});


async function openWs(): Promise<FakeWebSocket> {
  
  
  await Promise.resolve();
  return FakeWebSocket.last();
}

describe("用户场景 · 真前端状态机 + 可控事件源", () => {
  it("打字 → 发送 → 切到另一会话 → 切回：输入框不回填已发送内容", async () => {
    let sid = "";
    const ctx = () => ({ sid, project: "/proj", model: "parent",
                         onSessionCreated: (id: string) => { sid = id; } });
    saveInput(null, "发出去的话");
    const ok = await ctl.send(ctx(), "发出去的话");
    expect(ok).toBe(true);
    expect(sid).toBeTruthy();

    
    expect(readInput(sid)).toBe("");

    
    const other = "s-other";
    streamStore.ensure(other);
    ctl.setFocus(other);
    ctl.setFocus(sid);
    expect(readInput(sid)).toBe("");

    
    FakeWebSocket.last().emit({ type: "done", model: "m" });
    expect(readInput(sid)).toBe("");
  });

  it("发送失败：内容留在输入框、不标已发送", async () => {
    const bad = newCtl(() => { throw new Error("WS 不可达"); });
    
    vi.spyOn(globalThis, "setTimeout").mockImplementation(
      ((fn: () => void) => { fn(); return 0 as unknown as ReturnType<typeof setTimeout>; }) as never);
    const sid = "s-existing";
    db.set(sid, []);
    saveInput(sid, "没发出去的话");
    const ok = await bad.send({ sid, project: "/proj", model: "parent" }, "没发出去的话");
    expect(ok).toBe(false);
    expect(readInput(sid)).toBe("没发出去的话");
  });

  it("done 早于 turn_saved：不提前刷账本，回复不被抹掉", async () => {
    const sid = "s-timing";
    db.set(sid, []);
    streamStore.ensure(sid);
    ctl.setFocus(sid);
    await ctl.send({ sid, project: "/proj", model: "parent" }, "问题");
    const ws = FakeWebSocket.last();

    ws.emit({ type: "turn_start", id: "q1", from_queue: false });
    ws.emit({ type: "text", text: "回答内容" });
    
    ws.emit({ type: "done", model: "m" });
    expect(streamStore.get(sid).messages.filter((m) => m.role === "user")).toHaveLength(1);
    expect(streamStore.get(sid).busy).toBe(false);

    
    dbAppend(sid, { role: "user", content: "问题" },
                  { role: "assistant", content: "回答内容" });
    ws.emit({ type: "turn_saved" });
    await new Promise((r) => setTimeout(r, 20));
    const local = streamStore.get(sid).messages;
    expect(local.map((m) => m.role)).toEqual(["user", "assistant"]);
    expect(new Set(local.map((m) => m.content)).size).toBe(2);
  });

  it("断线重放同一批事件：消息不重复、游标不后退", async () => {
    const sid = "s-replay";
    db.set(sid, []);
    streamStore.ensure(sid);
    await ctl.send({ sid, project: "/proj", model: "parent" }, "重放测试");
    const ws = FakeWebSocket.last();
    ws.emit({ type: "turn_start", id: "q", _i: 1 });
    ws.emit({ type: "text", text: "重放", _i: 2 });
    ws.emit({ type: "done", model: "m", _i: 3 });
    const before = streamStore.get(sid).messages.length;

    
    await ctl.hydrate(sid, true);
    ws.emit({ type: "turn_start", id: "q", _i: 1 });
    ws.emit({ type: "text", text: "重放", _i: 2 });
    ws.emit({ type: "done", model: "m", _i: 3 });
    expect(streamStore.get(sid).messages.length).toBe(before);
  });

  it("回复中插队：两条都在尾部，顺序是自然发生顺序，不出现第二份", async () => {
    const sid = "s-queue";
    db.set(sid, []);
    streamStore.ensure(sid);
    await ctl.send({ sid, project: "/proj", model: "parent" }, "第一条");
    FakeWebSocket.last().emit({ type: "turn_start", id: "q1" });
    await ctl.send({ sid, project: "/proj", model: "parent" }, "第二条");

    const users = streamStore.get(sid).messages
      .filter((m) => m.role === "user").map((m) => m.content);
    expect(users).toEqual(["第一条", "第二条"]);
    expect(new Set(users).size).toBe(2);   

    
    expect(streamStore.get(sid).queue.some((q) => q.content === "第二条")).toBe(true);
  });

  it("队列满 3 条：第 5 条被拦，内容仍在输入框不丢", async () => {
    const sid = "s-full";
    db.set(sid, []);
    streamStore.ensure(sid);
    
    
    await ctl.send({ sid, project: "/proj", model: "parent" }, "1");
    FakeWebSocket.last().emit({ type: "turn_start", id: "q1" });
    for (const t of ["2", "3", "4"]) {
      expect(await ctl.send({ sid, project: "/proj", model: "parent" }, t)).toBe(true);
    }
    expect(streamStore.get(sid).queue).toHaveLength(3);
    const ok = await ctl.send({ sid, project: "/proj", model: "parent" }, "5");
    expect(ok).toBe(false);
    expect(streamStore.get(sid).queue).toHaveLength(3);   
    
    expect(readInput(sid)).toBe("5");
  });

  it("发送后 busy 只存在一份：控制器、hydrate、stop 读的都是同一个 store", async () => {
    const sid = "s-single-source";
    db.set(sid, []);
    streamStore.ensure(sid);
    await ctl.send({ sid, project: "/proj", model: "parent" }, "在跑吗");
    expect(streamStore.get(sid).busy).toBe(true);
    expect(ctl.isRunning(sid)).toBe(true);          
    expect(streamStore.get(sid).optimisticUntil).toBeGreaterThan(Date.now());

    
    await ctl.hydrate(sid, true);
    expect(streamStore.get(sid).busy).toBe(true);
    expect(ctl.isRunning(sid)).toBe(true);

    
    FakeWebSocket.last().emit({ type: "done", model: "m" });
    expect(streamStore.get(sid).busy).toBe(false);
    expect(ctl.isRunning(sid)).toBe(false);
    expect(streamStore.get(sid).optimisticUntil).toBe(0);
  });

  it("删除会话：本地草稿、状态、连接一起清，不影响别的会话", async () => {
    const a = "a", b = "b";
    saveInput(a, "A 的草稿");
    saveInput(b, "B 的草稿");
    streamStore.ensure(a);
    streamStore.ensure(b);
    streamStore.patch(a, { busy: true });
    ctl.dropSession(a);
    expect(readInput(a)).toBe("");   
    expect(readInput(b)).toBe("B 的草稿");
    expect(streamStore.get(b).busy).toBe(false);
    expect(streamStore.get(a).messages).toEqual([]);
  });
});
