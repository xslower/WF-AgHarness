
import { useCallback, useLayoutEffect, useRef } from "react";


const TOP_TRIGGER_PX = 80;

const REARM_PX = 240;

export interface LoadOlderResult {
  added: boolean;
  count: number;
}

export interface PagingDeps {
  
  scrollRef: React.RefObject<HTMLDivElement | null>;
  
  hasMore: boolean;
  
  onLoadOlder?: () => Promise<LoadOlderResult>;
  
  stickBottomRef: React.RefObject<boolean>;
  
  messages: unknown[];
}

export function useScrollPaging(deps: PagingDeps) {
  const { scrollRef, hasMore, onLoadOlder, stickBottomRef, messages } = deps;
  const loadingRef = useRef(false);
  
  const coolingRef = useRef(false);
  
  const pendingFixRef = useRef(0);

  
  const maybeLoadOlder = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    
    if (el.scrollTop > REARM_PX) coolingRef.current = false;

    if (!hasMore || !onLoadOlder || loadingRef.current || coolingRef.current) return;
    if (stickBottomRef.current) return;      
    if (el.scrollTop >= TOP_TRIGGER_PX) return;

    loadingRef.current = true;
    
    pendingFixRef.current = el.scrollHeight;
    void onLoadOlder().then((r) => {
      if (!r.added) {
        pendingFixRef.current = 0;
        coolingRef.current = false;   
      } else {
        coolingRef.current = true;
      }
      loadingRef.current = false;
    }).catch(() => {
      pendingFixRef.current = 0;
      loadingRef.current = false;
    });
  }, [hasMore, onLoadOlder, scrollRef, stickBottomRef]);

  
  useLayoutEffect(() => {
    const before = pendingFixRef.current;
    if (!before) return;
    pendingFixRef.current = 0;
    const el = scrollRef.current;
    if (el) el.scrollTop += el.scrollHeight - before;
  }, [messages, scrollRef]);

  return { maybeLoadOlder };
}
