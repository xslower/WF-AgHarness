
import type { PendingHumanItem, SessionAttentionRow } from "../api";
import { isFresh, type SeenMap } from "./seen";

export interface Attn {
  running: number;
  queued: number;
  approvals: number;
  plan: boolean;
  fresh: number;
  human: number;
}

export const EMPTY_ATTN: Attn = Object.freeze({
  running: 0, queued: 0, approvals: 0, plan: false, fresh: 0, human: 0,
}) as Attn;


export function sessionAttn(
  row: SessionAttentionRow | undefined,
  seen: SeenMap,
  curId?: string | null,
): Attn {
  if (!row) return EMPTY_ATTN;
  return {
    running: row.running ? 1 : 0,
    queued: row.queued || 0,
    approvals: row.approvals || 0,
    plan: !!row.plan,
    fresh: isFresh(row, seen, curId) ? 1 : 0,
    human: 0,
  };
}


export function mergeAttn(list: Attn[]): Attn {
  let out: Attn = { ...EMPTY_ATTN };
  for (const a of list) {
    out = {
      running: out.running + a.running,
      queued: out.queued + a.queued,
      approvals: out.approvals + a.approvals,
      plan: out.plan || a.plan,
      fresh: out.fresh + a.fresh,
      human: out.human + a.human,
    };
  }
  return out;
}


export function flowAttn(
  rows: SessionAttentionRow[],
  humans: PendingHumanItem[],
  project: string,
  name: string,
  seen: SeenMap,
  curId?: string | null,
): Attn {
  const own = rows.filter(
    (r) => r.kind === "workflow" && r.origin === name && (r.project || "") === (project || ""),
  );
  const gates = humans.filter(
    (h) => h.workflow === name && (h.project || "") === (project || ""),
  );
  return mergeAttn([
    ...own.map((r) => sessionAttn(r, seen, curId)),
    
    ...gates.map(() => ({ ...EMPTY_ATTN, human: 1 })),
  ]);
}


export function hasAny(a: Attn): boolean {
  return !!(a.running || a.queued || a.approvals || a.plan || a.fresh || a.human);
}


export function waitingCount(a: Attn): number {
  return a.approvals + a.human + (a.plan ? 1 : 0);
}
