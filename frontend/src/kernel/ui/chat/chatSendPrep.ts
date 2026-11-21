
import { api } from "../../api";
import { readPrefs, writePrefs } from "../../chat/sessionPrefs";
import { resetNewSessionSlot } from "../../chat/chatSessionStore";
import { streamStore } from "./sessionStore";
import type { TurnContext } from "./chatTypes";
export async function ensureSession(ctx: TurnContext, title: string): Promise<string> {
  if (ctx.sid) return ctx.sid;
  if (!ctx.project) {
    streamStore.patch("", {
      live: [...streamStore.get("").live,
             { kind: "error", text: "请先在上方下拉框选择一个项目，再开始对话" }],
    });
    return "";
  }
  const meta = ctx.sessionMeta || {};
  const s = await api.createSession(
    title.slice(0, 20) || "图片任务", ctx.project,
    meta.kind || "", meta.origin || "");
  streamStore.ensure(s.id);
  
  
  
  const local = readPrefs(null);
  if (local.model || local.workflow || local.plan) writePrefs(s.id, local);
  resetNewSessionSlot();   
  ctx.onSessionCreated?.(s.id);
  return s.id;
}

