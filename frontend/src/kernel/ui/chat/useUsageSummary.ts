
import { useEffect, useState } from "react";

import { api } from "../../api";
import type { UsageSummary } from "../../api";
import { readStored, writeStored } from "../useLocalState";

export interface UsageController {
  data: UsageSummary | null;
  open: Set<string>;
  toggle: (name: string) => void;
}

export function useUsageSummary(): UsageController {
  const [data, setData] = useState<UsageSummary | null>(null);
  
  const [open, setOpen] = useState<Set<string>>(
    () => new Set(readStored<string[]>("ui.usageOpen", [])));

  useEffect(() => {
    let alive = true;
    api.usageSummary()
      .then((d) => { if (alive) setData(d); })
      .catch(() => {  });
    return () => { alive = false; };
  }, []);

  const toggle = (name: string) => {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      writeStored("ui.usageOpen", [...next]);
      return next;
    });
  };

  return { data, open, toggle };
}
