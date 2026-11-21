
import { useEffect, useState } from "react";

import { api } from "../../api";
import type { AppConfig } from "../../api";
import { events } from "../../api/eventBridge";

export function useOwnConfig(outerConfig: AppConfig | null | undefined): AppConfig | null {
  const [own, setOwn] = useState<AppConfig | null>(null);

  useEffect(() => {
    if (outerConfig !== undefined) return;   
    const load = () => { void api.getConfig().then(setOwn).catch(() => setOwn(null)); };
    load();
    const offChanged = events.on("config.changed", load);
    
    
    const offRe = events.onReconnect(load);
    return () => { offChanged(); offRe(); };
  }, [outerConfig]);

  return outerConfig !== undefined ? outerConfig : own;
}
