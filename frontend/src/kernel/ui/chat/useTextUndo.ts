
import { useCallback, useRef } from "react";

export interface TextUndo {
  
  record: (text: string) => void;
  
  handleKey: (e: React.KeyboardEvent, setText: (v: string) => void) => boolean;
}

export function useTextUndo(): TextUndo {
  const stack = useRef<{ items: string[]; idx: number }>({ items: [""], idx: 0 });
  const lastEdit = useRef(0);

  const record = useCallback((text: string) => {
    const now = Date.now();
    const u = stack.current;
    if (now - lastEdit.current < 500 && u.idx === u.items.length - 1) {
      u.items[u.idx] = text;
    } else {
      u.items = u.items.slice(0, u.idx + 1);
      if (u.items[u.items.length - 1] !== text) u.items.push(text);
      u.idx = u.items.length - 1;
    }
    lastEdit.current = now;
  }, []);

  const handleKey = useCallback((e: React.KeyboardEvent,
                                 setText: (v: string) => void): boolean => {
    if (!(e.ctrlKey || e.metaKey)) return false;
    const k = e.key.toLowerCase();
    const u = stack.current;
    if (k === "z") {
      if (e.shiftKey) { if (u.idx < u.items.length - 1) u.idx += 1; }
      else if (u.idx > 0) u.idx -= 1;
    } else if (k === "y") {
      if (u.idx < u.items.length - 1) u.idx += 1;
    } else {
      return false;
    }
    e.preventDefault();
    setText(u.items[u.idx] ?? "");
    return true;
  }, []);

  return { record, handleKey };
}
