
import { useCallback, useMemo, useState } from "react";

export interface Selection {
  ids: Set<string>;
  toggle: (id: string) => void;
  clear: () => void;
  keepOnly: (alive: string[]) => void;
  size: number;
}

export function useSelection(): Selection {
  const [ids, setIds] = useState<Set<string>>(() => new Set());

  const toggle = useCallback((id: string) => {
    setIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const clear = useCallback(() => setIds(new Set()), []);

  const keepOnly = useCallback((alive: string[]) => {
    setIds((prev) => {
      const next = new Set([...prev].filter((x) => alive.includes(x)));
      return next.size === prev.size ? prev : next;
    });
  }, []);

  return useMemo(
    () => ({ ids, toggle, clear, keepOnly, size: ids.size }),
    [ids, toggle, clear, keepOnly]);
}
