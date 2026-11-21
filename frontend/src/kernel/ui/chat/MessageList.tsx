
import { useCallback, useMemo, useRef } from "react";
import type { AppConfig, ChatMessage } from "../../api";
import { Icon } from "../icons";
import { useScrollPaging } from "./useScrollPaging";
import { MessageRow } from "./MessageRow";
import { LiveBlocks } from "./LiveBlocks";
import { useChatScroll } from "./useChatScroll";
import { useTailMeta } from "./useTailMeta";
import { fmtClock, fmtCost, fmtTokens } from "./msgFormat";
import type { LiveEvent, SubAgent } from "../../chat/chatTypes";

interface Props {
  config: AppConfig | null;
  messages: ChatMessage[];
  live: LiveEvent[];
  busy: boolean;
  subAgents: Record<string, SubAgent>;
  activeSubAgent: string | null;
  setActiveSubAgent: (id: string | null) => void;
  suggestions: string[];
  onSend: (text: string) => void;
  onEdit: (index: number) => void;
  onQuerySubAgent?: (id: string) => void | Promise<void>;
  onMessageSubAgent?: (id: string, text: string) => void | Promise<boolean>;
  onStopSubAgent?: (id: string) => void | Promise<void>;
  maxWidth: number;
  
  sessionId?: string | null;
  
  msgOffset?: number;
  
  hasMore?: boolean;
  
  onLoadOlder?: () => Promise<{ added: boolean; count: number }>;
}

export function MessageList({
  config, messages, live, busy, subAgents, activeSubAgent, setActiveSubAgent,
  suggestions, onSend, onEdit, onQuerySubAgent, onMessageSubAgent,
  onStopSubAgent, maxWidth, sessionId, msgOffset = 0, hasMore = false, onLoadOlder,
}: Props) {
  
  
  
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const stickBottomRef = useRef(true);

  
  const { maybeLoadOlder } = useScrollPaging({
    scrollRef, hasMore, onLoadOlder, stickBottomRef, messages,
  });

  const scroll = useChatScroll({
    scrollRef, stickBottomRef, sessionId, messages, liveCount: live.length,
    onReachTop: maybeLoadOlder,
  });

  const tailMeta = useTailMeta(messages);

  
  const onEditRef = useRef(onEdit);
  onEditRef.current = onEdit;
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const editAt = useCallback((m: ChatMessage) => {
    const i = messagesRef.current.indexOf(m);
    if (i >= 0) onEditRef.current(i);
  }, []);

  
  const toolResults = useMemo(() => {
    const m = new Map<string, ChatMessage>();
    for (const msg of messages) {
      if (msg.role === "tool" && msg.tool_call_id) m.set(msg.tool_call_id, msg);
    }
    return m;
  }, [messages]);

  return (
    <div className="messages" ref={scrollRef} onScroll={scroll.onScroll}
      style={maxWidth ? { maxWidth, margin: "0 auto", width: "100%" } : undefined}>
      {messages.map((m, i) => (
        <MessageRow key={msgOffset + i} m={m} config={config}
          toolResults={toolResults} onEdit={editAt} />
      ))}
      {busy && !live.length && (
        <div className="msg assistant">
          <div className="msg-role">助手</div>
          <div className="msg-body thinking-dots">⏺⏺⏺</div>
        </div>
      )}
      <LiveBlocks live={live} reasonPreRef={scroll.reasonPreRef}
        subAgents={subAgents} activeSubAgent={activeSubAgent}
        setActiveSubAgent={setActiveSubAgent}
        onQuerySubAgent={onQuerySubAgent}
        onMessageSubAgent={onMessageSubAgent}
        onStopSubAgent={onStopSubAgent} />
      <div ref={scroll.bottomRef} />
      {!busy && suggestions.length > 0 && (
        <div className="suggestions">
          {suggestions.map((s, i) => (
            <button key={i} className="chip" onClick={() => onSend(s)}>{s}</button>
          ))}
        </div>
      )}
      {!busy && tailMeta && (
        <div className="msg-meta" title={tailMeta.hint}>
          {tailMeta.tokens > 0 && <span><Icon name="bolt" /> {fmtTokens(tailMeta.tokens)} tokens</span>}
          {tailMeta.cost > 0 && <span>· ¥{fmtCost(tailMeta.cost)}</span>}
          {tailMeta.ts > 0 && <span>· {fmtClock(tailMeta.ts)}</span>}
        </div>
      )}
      {}
      {!scroll.atBottom && (
        <div className="scroll-bottom-wrap">
          <button className="scroll-bottom" title="回到底部" onClick={scroll.scrollToBottom}>
            <Icon name="arrow-down" />
          </button>
        </div>
      )}
    </div>
  );
}
