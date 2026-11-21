

export interface SubAgentEvent {
  type?: string;
  text?: string;
  name?: string;
}

export interface EventBlock {
  kind: "text" | "reason" | "tool";
  text: string;
  
  name?: string;
}


const STRUCTURAL = new Set([
  "tool_start", "tool_end", "tool_call", "model", "usage", "debug",
]);

export function mergeSubAgentEvents(events: SubAgentEvent[]): EventBlock[] {
  const out: EventBlock[] = [];
  for (const e of events) {
    const type = String(e.type || "");
    const text = e.text ?? "";
    if (STRUCTURAL.has(type)) continue;
    
    const isTool = !!e.name || type === "tool_output";
    if (!isTool && !text.trim()) continue;   
    if (isTool) {
      const name = e.name || "工具";
      const last = out[out.length - 1];
      if (last?.kind === "tool" && last.name === name) last.text += text;
      else out.push({ kind: "tool", text, name });
      continue;
    }
    const kind: "text" | "reason" = type === "reason" ? "reason" : "text";
    const last = out[out.length - 1];
    if (last?.kind === kind) last.text += text;
    else out.push({ kind, text });
  }
  
  return out.filter((b) => b.kind !== "tool" || b.text.trim());
}
