
import { clearPartial, markInputSent, saveInput } from "./chatStorage";
import { IDLE_PLAN } from "./chatEvents";
import { MAX_QUEUE } from "./queueOps";
import {
  isEmptyTurn, makePayload, makeQid, makeUserMessage, type TurnInput,
} from "./chatPayload";
import { ensureSession } from "./chatSendPrep";
import { streamStore } from "./sessionStore";
import type { SendOptions, TurnContext } from "./chatTypes";

export interface SendDeps {
  pool: { connectWithRetry(sid: string): Promise<WebSocket> };
  
  partials: Map<string, unknown>;
  
  reviveSession: (sid: string) => void;
  setFocus: (sid: string | null) => void;
  
  scheduleRetry: (sid: string, why: string) => void;
}

export async function send(deps: SendDeps, ctx: TurnContext, body: string,
                           opts: SendOptions = {}): Promise<boolean> {
  const turn: TurnInput = {
    body,
    images: opts.images ?? [],
    audio: opts.audio ?? "",
    attachments: opts.attachments ?? [],
    workflow: opts.workflow,
    plan: opts.plan,
    model: ctx.model,
    policy: ctx.policy || "",
  };
  const { images, attachments } = turn;
  if (isEmptyTurn(turn)) return false;
  
  if (opts.plan === false && ctx.sid) streamStore.patch(ctx.sid, { planState: IDLE_PLAN });
  if (ctx.sid) streamStore.patch(ctx.sid, { suggestions: [] });

  try {
    const sid = await ensureSession(ctx, body);
    if (!sid) return false;
    return await dispatch(deps, ctx, turn, sid, body);
  } catch (e) {
    return failSend(deps, ctx, e);
  }
}


async function dispatch(deps: SendDeps, ctx: TurnContext, turn: TurnInput,
                        sid: string, body: string): Promise<boolean> {
  const { images, attachments } = turn;
  
  deps.partials.delete(sid);
  clearPartial(sid);
  deps.reviveSession(sid);   
  
  
  const qid = makeQid();
  saveInput(sid, body);
  const ws = await deps.pool.connectWithRetry(sid);
  const payload = makePayload(turn, qid);
  
  
  
  const OPTIMISTIC_MS = 5000;

  
  const prev = streamStore.get(sid);
  const queued = prev.busy;
  if (queued && prev.queue.length >= MAX_QUEUE) {
    streamStore.patch(sid, {
      live: [...prev.live, {
        kind: "error",
        text: `队列已满（${MAX_QUEUE} 条）：先删掉或撤回一条，把内容合并到后面统一发送`,
      }],
    });
    return false;
  }
  
  
  
  streamStore.patch(sid, {
    busy: true,
    optimisticUntil: Date.now() + OPTIMISTIC_MS,
    messages: [...prev.messages, makeUserMessage(body, images, attachments)],
    ...(queued ? {
      queue: [...prev.queue, {
        id: qid, content: body, images: images.length,
        attachments: attachments.map((a) => a.name),
        workflow: turn.workflow || "", interjecting: false,
      }],
    } : {}),
  });
  deps.setFocus(sid);
  ws.send(JSON.stringify(payload));
  
  markInputSent(sid, body);
  return true;
}


function failSend(deps: SendDeps, ctx: TurnContext, e: unknown): false {
  const key = ctx.sid || "";
  streamStore.patch(key, {
    busy: false,
    optimisticUntil: 0,
    live: [...streamStore.get(key).live, {
      kind: "error",
      text: `发送失败: ${e}。内容已存入本地草稿，可在输入框重新发送。`,
    }],
  });
  if (key) {
    
    
    deps.scheduleRetry(key, String(e));
  }
  return false;
}
