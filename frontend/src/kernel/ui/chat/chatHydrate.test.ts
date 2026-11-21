
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../api";
import { EventCursors } from "./eventCursor";
import { hydrate, type HydrateDeps } from "./chatHydrate";
import { resetStreamStoreForTest, streamStore } from "./sessionStore";

type Live = Record<string, unknown>;


function stubLive(live: Live): void {
  (api as unknown as { sessionLive: (sid: string, since?: number) => Promise<Live> })
    .sessionLive = async () => live;
}

function deps(): HydrateDeps & { ensured: string[] } {
  const ensured: string[] = [];
  return {
    cursors: new EventCursors(),
    flushStream: () => {},
    applyReplay: () => {},
    ensureSocket: async (sid: string) => { ensured.push(sid); },
    ensured,
  };
}

function snapshot(over: Live = {}): Live {
  return {
    sid: "s1", running: false, queue: [], connected: false, draft: [],
    stream: { text: "", reason: "" }, approvals: [],
    plan: { status: "idle", planText: "" }, lastSeq: 0, replay: [],
    ...over,
  };
}

const tick = () => new Promise((r) => setTimeout(r, 0));

describe("hydrate 的补连接判定", () => {
  const realLive = api.sessionLive;

  beforeEach(() => {
    resetStreamStoreForTest();
  });

  afterEach(() => {
    (api as unknown as { sessionLive: typeof realLive }).sessionLive = realLive;
  });

  it("后端还在跑 → 补连接（原有行为）", async () => {
    stubLive(snapshot({ running: true }));
    const d = deps();
    await hydrate("s1", true, d);
    await tick();
    expect(d.ensured).toEqual(["s1"]);
  });

  it("计划待确认（running=false）→ 也补连接（本次修的故障）", async () => {
    stubLive(snapshot({
      plan: { status: "awaiting_approval", planText: "## 📋 实施计划\n1. …" },
    }));
    const d = deps();
    await hydrate("s1", true, d);
    await tick();
    expect(d.ensured).toEqual(["s1"]);
    
    expect(streamStore.get("s1").planState.status).toBe("awaiting_approval");
  });

  it("有待审批项 → 也补连接", async () => {
    stubLive(snapshot({ approvals: [{ id: "a1", kind: "command", command: "rm -rf x" }] }));
    const d = deps();
    await hydrate("s1", true, d);
    await tick();
    expect(d.ensured).toEqual(["s1"]);
  });

  it("纯空闲会话 → 不补连接（否则侧栏点一遍就开一堆 WS）", async () => {
    stubLive(snapshot());
    const d = deps();
    await hydrate("s1", true, d);
    await tick();
    expect(d.ensured).toEqual([]);
  });
});
