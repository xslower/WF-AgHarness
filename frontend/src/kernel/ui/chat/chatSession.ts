
import type { ChatMessage } from "../../api";
import type { LiveEvent } from "./chatEvents";


function hasSomethingToShow(m: ChatMessage): boolean {
  if (m.role !== "assistant") return !isFunctionalUserMsg(m);
  if (m.tool_calls?.length) return true;
  if (m.reasoning) return true;
  const text = typeof m.content === "string"
    ? m.content.trim()
    : Array.isArray(m.content)
      ? m.content.some((p) => p.type === "text" && p.text?.trim())
      : false;
  return !!text;
}


function isFunctionalUserMsg(m: ChatMessage): boolean {
  if (m.role !== "user") return false;
  if (m._bg_job) return true;
  return m._sys === "bg_job" || m._sys === "subagent";
}



export function visibleMessages(messages: ChatMessage[]): ChatMessage[] {
  return messages.filter(hasSomethingToShow);
}

export interface PartialSnapshot {
  text: string;
  reason: string;
  ts?: number;
}


const STREAM_KINDS = new Set(["text", "reason"]);

function sameLive(a: LiveEvent, b: LiveEvent): boolean {
  return a.kind === b.kind && a.text === b.text;
}


export function mergeStream(
  live: LiveEvent[],
  stream?: { text?: string; reason?: string } | null,
): LiveEvent[] {
  const text = stream?.text || "";
  const reason = stream?.reason || "";
  if (!text.trim() && !reason.trim()) return live;

  let cut = live.length;
  while (cut > 0 && STREAM_KINDS.has(live[cut - 1].kind)) cut--;
  const head = live.slice(0, cut);
  const tail: LiveEvent[] = [];
  
  if (reason.trim()) tail.push({ kind: "reason", text: reason });
  if (text.trim()) tail.push({ kind: "text", text });

  
  
  
  
  const localTail = live.slice(cut);
  const merged = mergeStreamTail(localTail, tail);
  const next = [...head, ...merged];

  
  if (next.length === live.length && next.every((e, i) => sameLive(e, live[i]))) {
    return live;
  }
  return next;
}


function mergeStreamTail(local: LiveEvent[], remote: LiveEvent[]): LiveEvent[] {
  if (!local.length) return remote;
  if (!remote.length) return local;
  const out: LiveEvent[] = [];
  const kinds = new Set([...local, ...remote].map((e) => e.kind));
  for (const kind of kinds) {
    const a = local.filter((e) => e.kind === kind);
    const b = remote.filter((e) => e.kind === kind);
    
    const pick = (arr: LiveEvent[]) =>
      arr.reduce((best, e) => (e.text.length > best.text.length ? e : best),
        arr[0]);
    const chosen = a.length && b.length
      ? (pick(a).text.length >= pick(b).text.length ? pick(a) : pick(b))
      : (a.length ? pick(a) : pick(b));
    out.push(chosen);
  }
  
  out.sort((x, y) => (x.kind === "reason" ? -1 : y.kind === "reason" ? 1 : 0));
  return out;
}


export const PARTIAL_TTL_MS = 12 * 3600_000;

export function isPartialStale(p: PartialSnapshot | null | undefined,
                               now: number = Date.now()): boolean {
  return !!p && now - (p.ts || 0) > PARTIAL_TTL_MS;
}


export function shouldRestorePartial(
  messages: ChatMessage[], p: PartialSnapshot | null | undefined,
  now: number = Date.now(),
): boolean {
  if (!p || isPartialStale(p, now)) return false;
  if (!p.text.trim() && !p.reason.trim()) return false;
  const last = messages[messages.length - 1];
  if (!last) return false;                        
  if (last.role === "assistant") return false;   
  
  if (last.ts && p.ts && p.ts < last.ts * 1000 - 1000) return false;
  return true;
}


export function liveFromPartial(p: PartialSnapshot): LiveEvent[] {
  const hasText = !!p.text.trim();
  const hasReason = !!p.reason.trim();
  if (!hasText && !hasReason) return [];
  return [
    { kind: "notice", text: "上次回复因连接中断未完成，以下是已生成的内容",
      tag: "partial" },
    ...(hasReason ? [{ kind: "reason" as const, text: p.reason }] : []),
    ...(hasText ? [{ kind: "text" as const, text: p.text }] : []),
  ];
}
