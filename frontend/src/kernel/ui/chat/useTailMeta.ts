
import { useMemo } from "react";

import type { ChatMessage } from "../../api";
import { fmtTokens } from "./msgFormat";

export interface TailMeta {
  tokens: number;
  cost: number;
  ts: number;
  hint: string;
}

export function useTailMeta(messages: ChatMessage[]): TailMeta | null {
  return useMemo(() => {
    const last = messages[messages.length - 1];
    if (!last || last.role !== "assistant") return null;
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role !== "assistant") continue;
      const u = m.usage_total || m.usage || null;
      const tokens = u ? (u.prompt_tokens || 0) + (u.completion_tokens || 0) : 0;
      if (!tokens && !m.ts) continue;
      return {
        tokens,
        cost: m.cost || 0,
        ts: m.ts || 0,
        hint: u
          ? `输入 ${fmtTokens(u.prompt_tokens || 0)} / 输出 ${fmtTokens(u.completion_tokens || 0)}（整轮累计，含工具轮）`
          : "",
      };
    }
    return null;
  }, [messages]);
}
