import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EventBridge, matchTopic } from "./eventBridge";


class FakeWS {
  static last: FakeWS | null = null;
  static all: FakeWS[] = [];

  onopen: ((e: unknown) => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: unknown) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  closed = false;

  constructor(public url: string) {
    FakeWS.last = this;
    FakeWS.all.push(this);
  }

  close() {
    this.closed = true;
    this.onclose?.({});
  }

  send() {
    
  }

  open() {
    this.onopen?.({});
  }

  emit(obj: unknown) {
    this.onmessage?.({ data: JSON.stringify(obj) });
  }
}

const make = () =>
  new EventBridge({
    url: () => "ws://test/ws/events",
    WebSocketImpl: FakeWS as unknown as typeof WebSocket,
  });

beforeEach(() => {
  FakeWS.last = null;
  FakeWS.all = [];
});

afterEach(() => {
  vi.useRealTimers();
});

describe("matchTopic", () => {
  it("按段通配", () => {
    expect(matchTopic("*", "file.changed")).toBe(true);
    expect(matchTopic("file.*", "file.changed")).toBe(true);
    expect(matchTopic("file.*", "tool.fs_write")).toBe(false);
    expect(matchTopic("file.*", "file.changed.x")).toBe(false);
    expect(matchTopic("file.changed", "file.changed")).toBe(true);
  });
});

describe("EventBridge", () => {
  it("收到订阅的事件", () => {
    const bridge = make();
    const got: string[] = [];
    bridge.on("file.changed", (ev) => got.push(ev.topic));
    bridge.connect();
    FakeWS.last!.open();
    FakeWS.last!.emit({ seq: 1, topic: "file.changed", ts: 0, payload: { path: "a" } });
    expect(got).toEqual(["file.changed"]);
    bridge.dispose();
  });

  it("解绑后不再收到", () => {
    const bridge = make();
    const got: number[] = [];
    const off = bridge.on("file.changed", (ev) => got.push(ev.seq));
    bridge.connect();
    FakeWS.last!.open();
    off();
    FakeWS.last!.emit({ seq: 2, topic: "file.changed", payload: {} });
    expect(got).toEqual([]);
    bridge.dispose();
  });

  it("通配订阅与 sys.* 过滤", () => {
    const bridge = make();
    const got: string[] = [];
    bridge.on("file.*", (ev) => got.push(ev.topic));
    bridge.connect();
    const ws = FakeWS.last!;
    ws.open();
    ws.emit({ seq: 1, topic: "file.opened", payload: {} });
    ws.emit({ seq: 2, topic: "tool.fs_write", payload: {} });
    ws.emit({ seq: 0, topic: "sys.ping", payload: {} });
    expect(got).toEqual(["file.opened"]);
    bridge.dispose();
  });

  it("坏 JSON 被忽略", () => {
    const bridge = make();
    const got: string[] = [];
    bridge.on("*", (ev) => got.push(ev.topic));
    bridge.connect();
    const ws = FakeWS.last!;
    ws.open();
    ws.onmessage?.({ data: "not json" });
    expect(got).toEqual([]);
    bridge.dispose();
  });

  it("单个 handler 抛错不影响其它 handler", () => {
    const bridge = make();
    const got: number[] = [];
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    bridge.on("file.changed", () => {
      throw new Error("boom");
    });
    bridge.on("file.changed", (ev) => got.push(ev.seq));
    bridge.connect();
    FakeWS.last!.open();
    FakeWS.last!.emit({ seq: 3, topic: "file.changed", payload: {} });
    expect(got).toEqual([3]);
    spy.mockRestore();
    bridge.dispose();
  });

  it("断线重连后触发 onReconnect 且订阅仍有效", () => {
    vi.useFakeTimers();
    const bridge = make();
    const got: number[] = [];
    bridge.on("file.changed", (ev) => got.push(ev.seq));
    const reconnected = vi.fn();
    bridge.onReconnect(reconnected);
    bridge.connect();

    const first = FakeWS.last!;
    first.open();
    expect(bridge.status).toBe("open");

    first.close(); 
    vi.advanceTimersByTime(5000);

    const second = FakeWS.last!;
    expect(second).not.toBe(first);
    second.open();
    expect(reconnected).toHaveBeenCalledTimes(1);

    second.emit({ seq: 9, topic: "file.changed", payload: {} });
    expect(got).toEqual([9]);
    bridge.dispose();
  });

  it("close() 后不再自动重连", () => {
    vi.useFakeTimers();
    const bridge = make();
    bridge.connect();
    FakeWS.last!.open();
    const first = FakeWS.last!;
    bridge.close();
    vi.advanceTimersByTime(60_000);
    expect(FakeWS.last).toBe(first);
    expect(FakeWS.all).toHaveLength(1);
  });
});





describe("事件总线判活", () => {
  it("长时间收不到任何帧 → 主动断开并重连（模拟 NAT 静默回收）", () => {
    vi.useFakeTimers();
    const b = make();
    b.connect();
    const ws = FakeWS.last!;
    ws.open();
    expect(b.status).toBe("open");
    
    vi.advanceTimersByTime(100_000);
    expect(ws.closed).toBe(true);
    
    vi.advanceTimersByTime(2_000);
    expect(FakeWS.all.length).toBeGreaterThan(1);
    b.dispose();
  });

  it("有帧回来就不判死（sys.ping 也算活着）", () => {
    vi.useFakeTimers();
    const b = make();
    b.connect();
    const ws = FakeWS.last!;
    ws.open();
    for (let i = 0; i < 6; i++) {
      vi.advanceTimersByTime(25_000);          
      ws.emit({ seq: 0, topic: "sys.ping", ts: 0, payload: {} });
    }
    expect(ws.closed).toBe(false);
    b.dispose();
  });

  it("dispose 后不再重连、也不再判活", () => {
    vi.useFakeTimers();
    const b = make();
    b.connect();
    FakeWS.last!.open();
    b.dispose();
    const n = FakeWS.all.length;
    vi.advanceTimersByTime(200_000);
    expect(FakeWS.all.length).toBe(n);
  });
});
