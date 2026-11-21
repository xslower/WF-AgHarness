
import { readSession, writeField, writeFieldOk } from "../../chat/chatSessionStore";
import type { ChatMessage } from "../../api";

type Store = Record<string, unknown>;


interface InputDraft { v: string; ts: number; sent?: boolean }

function readRaw(sid: string | null | undefined): InputDraft | null {
  const e = readSession(sid).input;
  return e && typeof e.v === "string" ? e as unknown as InputDraft : null;
}


export function readInput(sid: string | null | undefined): string {
  const d = readRaw(sid);
  return d && d.sent !== true ? d.v : "";
}


export function saveInput(sid: string | null | undefined, text: string): void {
  if (!text) {
    if (readRaw(sid)?.sent === true) return;  
    writeField(sid, "input", undefined);
    return;
  }
  writeField(sid, "input", { v: text, ts: Date.now(), sent: false });
}


export function markInputSent(sid: string, content: string): void {
  writeField(sid, "input", { v: content, ts: Date.now(), sent: true });
}


export function clearSentInput(sid: string): void {
  if (readRaw(sid)?.sent === true) writeField(sid, "input", undefined);
}


export interface PartialReply {
  text: string;
  reason: string;
  ts: number;
}


const clearedPartials = new Set<string>();

export function savePartial(sid: string, d: PartialReply): void {
  clearedPartials.delete(sid);
  writeField(sid, "partial", d as unknown as Store);
}

export function readPartial(sid: string): PartialReply | null {
  if (clearedPartials.has(sid)) return null;
  const d = readSession(sid).partial;
  return d && typeof d.text === "string" ? d as unknown as PartialReply : null;
}

export function clearPartial(sid: string): void {
  
  if (writeFieldOk(sid, "partial", undefined)) clearedPartials.delete(sid);
  else clearedPartials.add(sid);
}




import type { DebugLog } from "../../chat/chatTypes";
export type { DebugLog };

export function historyOf(messages: ChatMessage[]): DebugLog[] {
  const hist: DebugLog[] = [];
  let round = 0;
  for (const m of messages) {
    if (m.role === "user") {
      round++;
      hist.push({
        event: "request", round, model: "", message_count: 0,
        last_user_msg: (typeof m.content === "string" ? m.content : "").slice(0, 500),
      });
    }
    if (m.role === "assistant") {
      hist.push({
        event: "response", round, model: m.model || "", usage: m.usage,
        has_tool_calls: !!m.tool_calls?.length,
        tool_calls: m.tool_calls?.map((tc) => ({
          name: tc.function?.name,
          arguments: tc.function?.arguments?.slice(0, 300),
        })),
        text_preview: (typeof m.content === "string" ? m.content : "").slice(0, 500),
        reasoning: m.reasoning?.slice(0, 500),
      });
    }
  }
  return hist;
}

export type CtxState = { used: number; model: string; estimated?: boolean };


export function usageFromDetail(
  s: { usage?: { used: number; model: string; estimated?: boolean } | null } | null,
): CtxState | null {
  const u = s?.usage;
  if (!u || !Number.isFinite(u.used) || u.used <= 0) return null;
  return { used: u.used, model: u.model || "", estimated: u.estimated === true };
}


export function lastCtxState(messages: ChatMessage[]): CtxState | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role === "assistant" && m.usage) {
      const used = (m.usage.prompt_tokens || 0) + (m.usage.completion_tokens || 0);
      if (used > 0) return { used, model: m.model || "", estimated: false };
    }
  }
  return null;
}
