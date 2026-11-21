import { afterEach, describe, expect, it, vi } from "vitest";
import { SOCKET_DEAD_AFTER_MS, HEARTBEAT_MS, MAX_WS_RETRY, SocketPool } from "./chatSocket";


class FakeWS {
  readyState = 0;              
  onopen: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev?: { code?: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  constructor(public url: string) {}

  send(data: string) { this.sent.push(data); }
  open() { this.readyState = 1; this.onopen?.(); }
  close(code = 1006) { this.readyState = 3; this.onclose?.({ code }); }
  fail() { this.onerror?.(); }
}

function setup(overrides: Partial<ConstructorParameters<typeof SocketPool>[0]> = {}) {
  const made: FakeWS[] = [];
  const dropped: string[] = [];
  const events: { sid: string; data: string }[] = [];
  const pool = new SocketPool({
    url: (sid) => `ws://test/ws/${sid}`,
    onMessage: (ev, sid) => { events.push({ sid, data: String((ev as MessageEvent).data) }); },
    onDrop: (sid) => { dropped.push(sid); },
    backoffMs: 0,
    wsFactory: (url) => {
      const ws = new FakeWS(url);
      made.push(ws);
      return ws as unknown as WebSocket;
    },
    ...overrides,
  });
  return { pool, made, dropped, events };
}

describe("连接复用", () => {
  it("同一会话已有存活连接时直接复用，不再新建", async () => {
    const { pool, made } = setup();
    const p = pool.connect("a");
    made[0].open();
    const first = await p;

    const second = await pool.connect("a");
    expect(second).toBe(first);
    expect(made).toHaveLength(1);
    expect(pool.activeSid).toBe("a");
  });

  it("连接已关闭则新建一条", async () => {
    const { pool, made } = setup();
    const p = pool.connect("a");
    made[0].open();
    await p;
    made[0].close();

    const p2 = pool.connect("a");
    made[1].open();
    expect(await p2).toBe(made[1]);
    expect(made).toHaveLength(2);
  });
});

describe("切会话", () => {
  it("focus 只切活跃指针，不关旧连接（关了会打断后端正在跑的那一轮）", async () => {
    const { pool, made } = setup();
    for (const sid of ["a", "b"]) {
      const p = pool.connect(sid);
      made[made.length - 1].open();
      await p;
    }
    pool.focus("a");
    expect(pool.activeSid).toBe("a");
    expect(made[0].readyState).toBe(1);
    expect(made[1].readyState).toBe(1);
  });

  it("focus(null) 清空活跃指针，连接本身不动", () => {
    const { pool } = setup();
    pool.focus(null);
    expect(pool.active).toBeNull();
    expect(pool.activeSid).toBeNull();
  });

  it("focus 到尚未连上的会话时回落为空", () => {
    const { pool } = setup();
    pool.focus("nobody");
    expect(pool.activeSid).toBeNull();
  });
});

describe("关闭与重连", () => {
  it("旧连接的 onclose 不会把新连接清掉（历史上的按钮错乱）", async () => {
    const { pool, made } = setup();
    const pa = pool.connect("a");
    made[0].open();
    await pa;

    const pb = pool.connect("b");
    made[1].open();
    await pb;
    expect(pool.activeSid).toBe("b");

    
    made[0].close();
    expect(pool.activeSid).toBe("b");
    expect(pool.active).toBe(made[1]);
  });

  it("已建立的连接断开且会话还在跑 → 触发 onDrop", async () => {
    const { pool, made, dropped } = setup();
    const p = pool.connect("a");
    made[0].open();
    await p;
    made[0].close();
    expect(dropped).toEqual(["a"]);
  });

  it("握手阶段就断开不触发 onDrop（交给重试处理）", async () => {
    const { pool, made, dropped } = setup();
    pool.connect("a").catch(() => {});  
    made[0].fail();
    made[0].close();
    expect(dropped).toEqual([]);
  });

  it("会话没在跑也要重连（前端以为的状态不可靠，done 丢了就永远不重连）", async () => {
    const { pool, made, dropped } = setup();
    const p = pool.connect("a");
    made[0].open();
    await p;
    made[0].close();
    expect(dropped).toEqual(["a"]);
  });

  it("后端说会话不存在（4404）不重连，避免无限重试", async () => {
    const { pool, made, dropped } = setup();
    const p = pool.connect("a");
    made[0].open();
    await p;
    made[0].close(4404);
    expect(dropped).toEqual([]);
  });
});

describe("重试", () => {
  
  async function waitFor(cond: () => boolean, ms = 500) {
    const t0 = Date.now();
    while (!cond()) {
      if (Date.now() - t0 > ms) throw new Error("等待超时");
      await new Promise((r) => setTimeout(r, 1));
    }
  }

  it("握手失败按次数重试，耗尽后抛出带原因的错", async () => {
    const { pool, made } = setup();
    const p = pool.connectWithRetry("a");
    for (let i = 0; i < MAX_WS_RETRY; i++) {
      await waitFor(() => made.length > i);
      made[i].fail();
      made[i].close();
    }
    await expect(p).rejects.toThrow(/已重试 4 次/);
    expect(made).toHaveLength(MAX_WS_RETRY);
  });

  it("第二次就成功时不再重试", async () => {
    const { pool, made } = setup();
    const p = pool.connectWithRetry("a");
    await waitFor(() => made.length === 1);
    made[0].fail();
    made[0].close();
    await waitFor(() => made.length === 2);
    made[1].open();
    await expect(p).resolves.toBe(made[1]);
    expect(made).toHaveLength(2);
  });
});

describe("事件转发", () => {
  it("消息按所属会话 id 转出去（hook 据此做归属判定）", async () => {
    const { pool, made, events } = setup();
    const p = pool.connect("s1");
    made[0].open();
    await p;
    made[0].onmessage?.({ data: '{"type":"text"}' } as MessageEvent);
    expect(events).toEqual([{ sid: "s1", data: '{"type":"text"}' }]);
  });
});




describe("心跳判死", () => {
  afterEach(() => {
    vi.useRealTimers();
    delete (globalThis as { document?: unknown }).document;
  });

  
  async function opened(hidden: boolean) {
    (globalThis as { document?: unknown }).document = { hidden };
    vi.useFakeTimers();
    const { pool, made, dropped } = setup();
    const p = pool.connect("a");
    made[0].open();
    await p;
    return { pool, ws: made[0], dropped };
  }

  it("前台超过 45s 没收到任何帧 → 主动断开触发重连", async () => {
    const { ws, dropped } = await opened(false);
    vi.advanceTimersByTime(HEARTBEAT_MS * 3 + 100);
    expect(ws.readyState).toBe(3);            
  });

  it("有 pong 回来就不判死", async () => {
    const { ws } = await opened(false);
    for (let i = 0; i < 4; i++) {
      vi.advanceTimersByTime(HEARTBEAT_MS);
      ws.onmessage?.({ data: '{"type":"pong"}' } as MessageEvent);   
    }
    expect(ws.readyState).toBe(1);
  });

  it("后台标签页不判死（定时器被浏览器节流时不能误杀连接）", async () => {
    
    
    const { ws } = await opened(true);
    vi.advanceTimersByTime(SOCKET_DEAD_AFTER_MS * 3);
    expect(ws.readyState).toBe(1);            
    expect(ws.sent.filter((s) => s.includes("ping")).length).toBeGreaterThan(0);
  });

  it("poke 会把判活基准重置到现在（回前台时调用）", async () => {
    const { pool, ws } = await opened(false);
    vi.advanceTimersByTime(SOCKET_DEAD_AFTER_MS - 5_000);   
    pool.poke("a");
    vi.advanceTimersByTime(HEARTBEAT_MS);
    expect(ws.readyState).toBe(1);            
  });

  it("knownSids 返回持有连接的会话（回前台逐个 poke 用）", async () => {
    const { pool } = await opened(false);
    expect(pool.knownSids()).toEqual(["a"]);
  });
});
