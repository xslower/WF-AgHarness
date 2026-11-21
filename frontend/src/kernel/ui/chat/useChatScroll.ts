
import { useCallback, useEffect, useRef, useState } from "react";

import type { ChatMessage } from "../../api";
import { readField, writeField } from "../../chat/chatSessionStore";


const STICK_PX = 24;

const LOAD_OLDER_PX = 80;

const SAVE_THROTTLE_MS = 250;

const GLIDE_GUARD_MS = 600;

export interface ChatScroll {
  bottomRef: React.RefObject<HTMLDivElement>;
  reasonPreRef: React.RefObject<HTMLPreElement>;
  stickBottomRef: React.MutableRefObject<boolean>;
  atBottom: boolean;
  onScroll: () => void;
  scrollToBottom: () => void;
}

export function useChatScroll(opts: {
  
  scrollRef: React.RefObject<HTMLDivElement>;
  
  stickBottomRef: React.MutableRefObject<boolean>;
  sessionId?: string | null;
  
  messages: ChatMessage[];
  liveCount: number;
  
  onReachTop: () => void;
}): ChatScroll {
  const { scrollRef, stickBottomRef, sessionId, messages, liveCount, onReachTop } = opts;
  const bottomRef = useRef<HTMLDivElement | null>(null);
  
  const glidingRef = useRef(false);
  const prevSidRef = useRef<string | null | undefined>(undefined);
  const pendingRestoreRef = useRef(false);
  const restoreMsgsRef = useRef<ChatMessage[] | null>(null);
  const saveTimerRef = useRef<number | null>(null);
  
  const saveKeyRef = useRef<string>("");
  const reasonPreRef = useRef<HTMLPreElement | null>(null);
  const [atBottom, setAtBottom] = useState(true);

  const scrollKey = sessionId ? sessionId : "";   
  
  const reachTop = useRef(onReachTop);
  reachTop.current = onReachTop;

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    
    if (glidingRef.current) {
      const done = el.scrollHeight - el.scrollTop - el.clientHeight < 4;
      if (done) glidingRef.current = false;
      stickBottomRef.current = true;
      setAtBottom(true);
      return;
    }
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_PX;
    
    stickBottomRef.current = near;
    setAtBottom(near);
    
    if (el.scrollTop < LOAD_OLDER_PX) reachTop.current();
    if (!scrollKey) return;
    
    
    
    
    
    
    
    const pendingForThis = saveTimerRef.current !== null
      && saveKeyRef.current === scrollKey;
    if (pendingForThis) return;
    const top = Math.round(el.scrollTop);
    saveTimerRef.current = window.setTimeout(() => {
      saveTimerRef.current = null;
      writeField(scrollKey, "scroll", top);
    }, SAVE_THROTTLE_MS);
    saveKeyRef.current = scrollKey;
  };

  
  useEffect(() => {
    if (prevSidRef.current === sessionId) return;
    prevSidRef.current = sessionId;
    pendingRestoreRef.current = true;
    restoreMsgsRef.current = messages;
    
    
    
  }, [sessionId]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (pendingRestoreRef.current) {
      
      if (restoreMsgsRef.current === messages) return;
      pendingRestoreRef.current = false;
      restoreMsgsRef.current = null;
      const top = scrollKey ? readField(scrollKey, "scroll", 0) : NaN;
      if (!Number.isFinite(top) || top <= 0) {
        el.scrollTop = el.scrollHeight;
        stickBottomRef.current = true;
        setAtBottom(true);
      } else {
        el.scrollTop = top;
        const near = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_PX;
        stickBottomRef.current = near;
        setAtBottom(near);
      }
      return;
    }
    if (stickBottomRef.current) {
      
      if (liveCount) el.scrollTop = el.scrollHeight;
      else bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      setAtBottom(true);
    }
    
    const pre = reasonPreRef.current;
    if (pre && stickBottomRef.current) {
      const nearPre = pre.scrollHeight - pre.scrollTop - pre.clientHeight < STICK_PX;
      if (nearPre) pre.scrollTop = pre.scrollHeight;
    }
  }, [messages, liveCount, scrollKey]);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    glidingRef.current = true;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    stickBottomRef.current = true;
    setAtBottom(true);
    
    window.setTimeout(() => { glidingRef.current = false; }, GLIDE_GUARD_MS);
  }, []);

  return { bottomRef, reasonPreRef, stickBottomRef, atBottom, onScroll, scrollToBottom };
}
