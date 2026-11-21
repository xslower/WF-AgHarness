
import { api } from "../../api";
import { normalizeSpec } from "../../model/modelSpec";
import { readPrefs } from "../../chat/sessionPrefs";
import { confirmDialog } from "../dialog";
import { cancelInterject, markInterjecting } from "./queueOps";
import { extractText } from "../markdown";
import { visibleMessages } from "./chatSession";
import { streamStore } from "./sessionStore";


const pendingDecisions = new Set<string>();


export function releasePlanDecision(sid: string): void {
  pendingDecisions.delete(sid);
}


export function resetPlanDecisionLocks(): void {
  pendingDecisions.clear();
}

export interface ActionsDeps {
  
  socketOf: (sid: string | null) => WebSocket | null | undefined;
  
  ensureSocket: (sid: string) => Promise<void>;
}

function sendIfOpen(deps: ActionsDeps, sid: string | null, msg: unknown): boolean {
  const ws = deps.socketOf(sid);
  if (!ws || ws.readyState !== WebSocket.OPEN) return false;
  ws.send(JSON.stringify(msg));
  return true;
}


function waitOpen(ws: WebSocket, timeoutMs = 8000): Promise<boolean> {
  if (ws.readyState === WebSocket.OPEN) return Promise.resolve(true);
  if (ws.readyState !== WebSocket.CONNECTING) return Promise.resolve(false);
  return new Promise<boolean>((resolve) => {
    let settled = false;
    const finish = (ok: boolean) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      ws.removeEventListener?.("open", onOpen);
      ws.removeEventListener?.("close", onGone);
      ws.removeEventListener?.("error", onGone);
      resolve(ok);
    };
    const onOpen = () => finish(true);
    const onGone = () => finish(false);
    const timer = setTimeout(() => finish(false), timeoutMs);
    ws.addEventListener?.("open", onOpen);
    ws.addEventListener?.("close", onGone);
    ws.addEventListener?.("error", onGone);
  });
}


function notice(sid: string, text: string, kind: "error" | "notice" = "error"): void {
  const cur = streamStore.get(sid);
  streamStore.patch(sid, { live: [...cur.live, { kind, text }] });
}

export async function stop(deps: ActionsDeps, sid: string | null): Promise<void> {
  const key = sid || "";
  const ws = deps.socketOf(sid);
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    
    streamStore.patch(key, { busy: false, optimisticUntil: 0, stopping: false });
    return;
  }
  streamStore.patch(key, { stopping: true });
  ws.send(JSON.stringify({ type: "stop" }));
}

export function queueAction(deps: ActionsDeps, sid: string | null,
                            action: "remove" | "interject" | "cancel_interject",
                            id: string): void {
  const key = sid || "";
  const cur = streamStore.get(key);
  if (action === "interject") {
    streamStore.patch(key, { queue: markInterjecting(cur.queue, id) });
  } else if (action === "cancel_interject") {
    streamStore.patch(key, { queue: cancelInterject(cur.queue, id) });
  } else {
    streamStore.patch(key, { queue: cur.queue.filter((x) => x.id !== id) });
  }
  sendIfOpen(deps, sid, { type: "queue_action", action, id });
}


export async function sendPlanDecision(deps: ActionsDeps, sid: string | null,
                                       decision: string, feedback?: string,
                                       plan?: string): Promise<void> {
  if (!sid) {
    notice("", "会话还没建立，无法提交计划决策");
    return;
  }
  
  
  
  
  if (pendingDecisions.has(sid)) return;
  pendingDecisions.add(sid);
  const done = () => pendingDecisions.delete(sid);
  
  
  const msg = { type: "plan_decision", decision, feedback, plan,
                model: normalizeSpec(readPrefs(sid).model) };
  
  if (sendIfOpen(deps, sid, msg)) return;
  
  const inflight = deps.socketOf(sid);
  if (inflight && inflight.readyState === WebSocket.CONNECTING) {
    if (await waitOpen(inflight) && sendIfOpen(deps, sid, msg)) return;
  }
  
  if (!inflight || inflight.readyState > WebSocket.OPEN) {
    try {
      await deps.ensureSocket(sid);
    } catch {
      
    }
    if (sendIfOpen(deps, sid, msg)) return;
  }
  
  done();
  notice(sid, "⚠ 提交计划决策失败：与后端的连接没建立起来，正在自动重连。"
    + "稍等几秒再点一次即可（计划状态不会丢）。");
}


export function removeApproval(sid: string | null, id: string): void {
  const key = sid || "";
  const cur = streamStore.get(key);
  streamStore.patch(key, { pendingApprovals: cur.pendingApprovals.filter((x) => x.id !== id) });
}

export function clearDebugLogs(sid: string | null): void {
  streamStore.patch(sid || "", { debugLogs: [] });
}

export async function editFrom(sid: string | null, index: number): Promise<string | null> {
  if (!sid) return null;
  const cur = streamStore.get(sid);
  const m = cur.messages[index];
  if (!m) return null;
  const text = extractText(m.content);
  if (!(await confirmDialog({
    title: "编辑消息",
    danger: true,
    okText: "回滚并编辑",
    message: "编辑这条消息？其后所有上下文将被删除（回滚），编辑后重新发送。",
  }))) return null;
  
  
  
  const absolute = cur.msgOffset + index;
  await api.truncate(sid, absolute);
  
  
  
  const win = await api.getSession(sid, 2).catch(() => null);
  if (win) {
    streamStore.patch(sid, {
      messages: visibleMessages(win.messages),
      msgOffset: win.offset ?? 0,
      hasMore: !!win.has_more,
      live: [],
    });
  } else {
    streamStore.patch(sid, { live: [] });
  }
  return text;
}
