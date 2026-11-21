
import { beforeEach, describe, expect, it } from "vitest";
import { releasePlanDecision, resetPlanDecisionLocks, sendPlanDecision, type ActionsDeps } from "./chatActions";
import { resetStreamStoreForTest, streamStore } from "./sessionStore";

const WS_OPEN = 1;
const WS_CONNECTING = 0;
const WS_CLOSED = 3;


class FakeWS {
  readyState: number;
  sent: string[] = [];
  private listeners = new Map<string, Set<() => void>>();
  constructor(public url = "ws://test", state = WS_OPEN) { this.readyState = state; }

  addEventListener(type: string, fn: () => void) {
    let set = this.listeners.get(type);
    if (!set) this.listeners.set(type, (set = new Set()));
    set.add(fn);
  }
  removeEventListener(type: string, fn: () => void) {
    this.listeners.get(type)?.delete(fn);
  }
  
  open() {
    this.readyState = WS_OPEN;
    for (const fn of [...(this.listeners.get("open") ?? [])]) fn();
  }
  close() {
    this.readyState = WS_CLOSED;
    for (const fn of [...(this.listeners.get("close") ?? [])]) fn();
  }
  send(data: string) { this.sent.push(data); }
  asWs(): WebSocket { return this as unknown as WebSocket; }
}

function deps(over: Partial<ActionsDeps> = {}) {
  const ensures: string[] = [];
  const base: ActionsDeps = {
    socketOf: () => null,
    ensureSocket: async (sid: string) => { ensures.push(sid); },
    ...over,
  };
  return { deps: base, ensures };
}

const sentOf = (ws: FakeWS) => ws.sent.map((s) => JSON.parse(s));

describe("计划决策：连接不可用时不能静默丢弃", () => {
  beforeEach(() => {
    resetStreamStoreForTest();
    resetPlanDecisionLocks();
  });

  it("有活连接时直接发，不补建", async () => {
    const ws = new FakeWS();
    const { deps: d, ensures } = deps({ socketOf: () => ws.asWs() });
    await sendPlanDecision(d, "s1", "approve");
    expect(sentOf(ws)).toEqual([{ type: "plan_decision", decision: "approve",
                                 model: "parent" }]);
    expect(ensures).toEqual([]);
  });

  it("没有连接 → 先补建（走 ensureSocket）再发帧", async () => {
    const ws = new FakeWS();
    let sock: WebSocket | null = null;
    const asked: string[] = [];
    const { deps: d } = deps({
      socketOf: () => sock,
      
      ensureSocket: async (sid: string) => { asked.push(sid); sock = ws.asWs(); },
    });
    await sendPlanDecision(d, "s1", "approve");
    expect(asked).toEqual(["s1"]);            
    expect(sentOf(ws)[0].decision).toBe("approve");
    
    expect(streamStore.get("s1").live).toEqual([]);
  });

  it("连接正在握手（CONNECTING）→ 等它 open 再发，不算失败", async () => {
    const ws = new FakeWS("ws://test", WS_CONNECTING);
    const { deps: d } = deps({ socketOf: () => ws.asWs() });
    const p = sendPlanDecision(d, "s1", "cancel");
    
    queueMicrotask(() => ws.open());
    await p;
    expect(sentOf(ws)).toEqual([{ type: "plan_decision", decision: "cancel",
                                 model: "parent" }]);
    expect(streamStore.get("s1").live).toEqual([]);
  });

  it("补建也失败 → 落一条可见提示（而不是让弹窗僵在原地）", async () => {
    const { deps: d } = deps({ ensureSocket: async () => {  } });
    await sendPlanDecision(d, "s1", "approve");
    const live = streamStore.get("s1").live;
    expect(live).toHaveLength(1);
    expect(live[0].kind).toBe("error");
    expect(live[0].text).toContain("计划决策");
  });

  it("sid 还没有（新会话）→ 直接提示，不去建连接", async () => {
    const { deps: d, ensures } = deps();
    await sendPlanDecision(d, null, "approve");
    expect(ensures).toEqual([]);
    expect(streamStore.get("").live[0].text).toContain("无法提交计划决策");
  });
});


describe("计划决策：连点只发一帧", () => {
  beforeEach(() => {
    resetStreamStoreForTest();
    resetPlanDecisionLocks();
  });

  it("同一会话同一决策连点 → 只发一帧", async () => {
    const ws = new FakeWS();
    const { deps: d } = deps({ socketOf: () => ws.asWs() });
    
    const calls = [
      sendPlanDecision(d, "s1", "approve"),
      sendPlanDecision(d, "s1", "approve"),
      sendPlanDecision(d, "s1", "approve"),
    ];
    await Promise.all(calls);
    expect(sentOf(ws)).toHaveLength(1);
    expect(sentOf(ws)[0].decision).toBe("approve");
  });

  it("同一张卡上不同决策也互斥（approve 后 cancel 被挡住）", async () => {
    const ws = new FakeWS();
    const { deps: d } = deps({ socketOf: () => ws.asWs() });
    await sendPlanDecision(d, "s1", "approve");
    await sendPlanDecision(d, "s1", "cancel");   
    expect(sentOf(ws).map((m) => m.decision)).toEqual(["approve"]);
  });

  it("后端回执到达后解锁 → 新一轮拍板能正常提交", async () => {
    const ws = new FakeWS();
    const { deps: d } = deps({ socketOf: () => ws.asWs() });
    await sendPlanDecision(d, "s1", "approve");
    releasePlanDecision("s1");                  
    await sendPlanDecision(d, "s1", "approve");
    expect(sentOf(ws).map((m) => m.decision)).toEqual(["approve", "approve"]);
  });

  it("发送失败自动解锁 → 用户可以再点一次", async () => {
    const ws = new FakeWS();
    let sock: WebSocket | null = null;
    const { deps: d } = deps({
      socketOf: () => sock,
      ensureSocket: async () => {  },
    });
    
    await sendPlanDecision(d, "s2", "approve");
    expect(sentOf(ws)).toHaveLength(0);
    expect(streamStore.get("s2").live[0].kind).toBe("error");
    
    sock = ws.asWs();
    await sendPlanDecision(d, "s2", "approve");
    expect(sentOf(ws)).toHaveLength(1);
  });
});
