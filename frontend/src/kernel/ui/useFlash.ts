
import { useCallback, useEffect, useRef, useState } from "react";

export type Flash = (text: string, ms?: number) => void;

export function useFlash(defaultMs = 3000) {
  const [msg, setMsg] = useState("");
  const timer = useRef<number | null>(null);

  const clear = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  useEffect(() => clear, [clear]);

  const flash = useCallback<Flash>((text, ms) => {
    setMsg(text);
    clear();
    timer.current = window.setTimeout(() => {
      setMsg("");
      timer.current = null;
    }, ms ?? defaultMs);
  }, [clear, defaultMs]);

  
  const flashErr = useCallback<Flash>(
    (text, ms) => flash(`✗ ${text}`, ms ?? Math.max(defaultMs, 5000)),
    [flash, defaultMs]);

  return { msg, setMsg, flash, flashErr };
}
