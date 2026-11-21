
import { api } from "../../api";
import type { ChatMessage } from "../../api";
import { visibleMessages } from "./chatSession";
import { streamStore } from "./sessionStore";


export const PAGE_SIZE = 150;


const loading = new Set<string>();

export interface LoadOlderResult {
  
  added: boolean;
  
  count: number;
}

export async function loadOlder(sid: string | null): Promise<LoadOlderResult> {
  const none: LoadOlderResult = { added: false, count: 0 };
  if (!sid) return none;
  const cur = streamStore.get(sid);
  if (!cur.hasMore || loading.has(sid)) return none;
  loading.add(sid);
  try {
    const page = await api.sessionMessagesBefore(sid, cur.msgOffset, PAGE_SIZE);
    const older: ChatMessage[] = visibleMessages(page.messages || []);
    if (!older.length) {
      
      streamStore.patch(sid, { hasMore: false });
      return none;
    }
    
    const now = streamStore.get(sid);
    streamStore.patch(sid, {
      messages: [...older, ...now.messages],
      msgOffset: page.offset ?? Math.max(0, cur.msgOffset - older.length),
      hasMore: !!page.has_more,
    });
    return { added: true, count: older.length };
  } catch {
    
    return none;
  } finally {
    loading.delete(sid);
  }
}

