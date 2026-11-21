
import type { ChatMessage } from "../../api";

export interface WindowInput {
  messages: ChatMessage[];
  offset: number;
  
  hasMore?: boolean;
}

export interface MergedWindow {
  messages: ChatMessage[];
  offset: number;
  hasMore: boolean;
}


export function mergeWindow(
  prev: WindowInput,
  incoming: WindowInput,
  incomingHasMore: boolean,
): MergedWindow {
  if (!incoming.messages.length) {
    return { messages: prev.messages, offset: prev.offset,
      hasMore: prev.hasMore ?? incomingHasMore };
  }
  const inOffset = Math.max(0, incoming.offset);
  
  const keep = Math.min(prev.messages.length, Math.max(0, inOffset - prev.offset));
  const head = prev.messages.slice(0, keep);
  
  const localExtra = prev.messages.slice(keep + incoming.messages.length);
  return {
    messages: [...head, ...incoming.messages, ...localExtra],
    offset: head.length ? prev.offset : inOffset,
    
    
    hasMore: head.length ? (prev.hasMore ?? incomingHasMore) : incomingHasMore,
  };
}
