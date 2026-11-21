
import { useEffect, useRef } from "react";

import { api } from "../../api";
import type { SessionDetail } from "../../api";
import { readPrefs } from "../../chat/sessionPrefs";

export function useEmbeddedHistory(opts: {
  
  external: boolean;
  activeSid: string | null;
  loadSession: (s: SessionDetail) => void;
  onModel: (model: string) => void;
}) {
  const { external, activeSid, loadSession, onModel } = opts;
  
  const latest = useRef({ loadSession, onModel });
  latest.current = { loadSession, onModel };

  useEffect(() => {
    if (external || !activeSid) return;
    
    const local = readPrefs(activeSid).model;
    if (typeof local === "string") latest.current.onModel(local);
    let cancelled = false;
    api.getSession(activeSid)
      .then((s) => {
        if (cancelled) return;
        latest.current.loadSession(s);
      })
      .catch(() => {  });
    return () => { cancelled = true; };
  }, [activeSid, external]);
}
