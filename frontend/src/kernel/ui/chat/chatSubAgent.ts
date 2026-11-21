
import { api } from "../../api";
import { streamStore } from "./sessionStore";

export function setActiveSubAgent(sid: string | null, id: string | null): void {
  streamStore.patch(sid || "", { activeSubAgent: id });
}

export async function querySubAgent(sid: string | null, id: string): Promise<void> {
  const parent = sid || "";
  const [detail, result] = await Promise.all([
    api.getSubagent(id, parent),
    api.subagentResult(id, parent).catch(() => null),
  ]);
  const cur = streamStore.get(parent);
  const sa = cur.subAgents[id];
  if (!sa) return;
  streamStore.patch(parent, {
    subAgents: {
      ...cur.subAgents,
      [id]: {
        ...sa,
        messages: detail.messages,
        events: detail.events as never,
        result: result?.content ?? sa.result,
      },
    },
  });
}

export async function messageSubAgent(sid: string | null, id: string,
                                       text: string): Promise<boolean> {
  try {
    await api.messageSubagent(id, text, sid || "");
    return true;
  } catch (e) {
    const key = sid || "";
    streamStore.patch(key, {
      live: [...streamStore.get(key).live, { kind: "error", text: `追加指令失败: ${e}` }],
    });
    return false;
  }
}

export async function stopSubAgent(sid: string | null, id: string): Promise<void> {
  const key = sid || "";
  try {
    await api.stopSubagent(id, sid || "");
    const cur = streamStore.get(key);
    const sa = cur.subAgents[id];
    if (sa) {
      streamStore.patch(key, { subAgents: { ...cur.subAgents, [id]: { ...sa, status: "stopped" } } });
    }
  } catch (e) {
    streamStore.patch(key, {
      live: [...streamStore.get(key).live, { kind: "error", text: `中止失败: ${e}` }],
    });
  }
}
