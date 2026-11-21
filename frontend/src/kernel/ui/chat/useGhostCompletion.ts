
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../api";

const DEBOUNCE_MS = 600;

const MIN_CHARS = 3;

export interface GhostOptions {
  sessionId: string | null;
  
  enabled: boolean;
}

export interface GhostCompletion {
  ghost: string;
  
  request: (text: string) => void;
  clear: () => void;
}

export function useGhostCompletion(opts: GhostOptions): GhostCompletion {
  const [ghost, setGhost] = useState("");
  const timer = useRef<number | null>(null);
  const lastReq = useRef("");
  const inputRef = useRef("");
  
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const cancel = useCallback(() => {
    if (timer.current) { window.clearTimeout(timer.current); timer.current = null; }
  }, []);

  const request = useCallback((text: string) => {
    inputRef.current = text;
    cancel();
    const o = optsRef.current;
    if (!o.enabled || text.trim().length < MIN_CHARS) {
      setGhost("");
      return;
    }
    timer.current = window.setTimeout(async () => {
      if (lastReq.current === text) return;
      lastReq.current = text;
      const r = await api.suggestInput(text, o.sessionId ?? "").catch(() => null);
      
      if (inputRef.current !== text) { setGhost(""); return; }
      setGhost(r?.completion ?? "");
    }, DEBOUNCE_MS);
  }, [cancel]);

  const clear = useCallback(() => { cancel(); setGhost(""); lastReq.current = ""; }, [cancel]);

  
  useEffect(() => {
    if (!opts.enabled) { cancel(); setGhost(""); lastReq.current = ""; }
  }, [opts.enabled, cancel]);

  
  useEffect(() => cancel, [cancel]);

  return { ghost, request, clear };
}
