
import { useEffect, useRef } from "react";

import { api } from "../../kernel/api";
import type { AppConfig, UtilityModels } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";

const EMPTY_UTILITY: UtilityModels = { completion: [], classify: [], review: [], suggest: [] };

export function useQueueAutoSave(
  draft: AppConfig,
  flash: (text: string, ms?: number) => void,
  flashErr: (text: string, ms?: number) => void,
  delayMs = 800,
) {
  const autoSaved = useRef<string | null>(null);
  const pending = useRef<{
    sig: string;
    queues: AppConfig["queues"];
    utility: UtilityModels;
  } | null>(null);
  const timer = useRef<number | null>(null);

  const queueSig = JSON.stringify([draft.queues, draft.utility ?? null]);

  const flush = async () => {
    if (timer.current !== null) { window.clearTimeout(timer.current); timer.current = null; }
    const p = pending.current;
    if (!p) return;
    pending.current = null;
    try {
      await api.setQueue(p.queues.parent, p.queues.child, p.queues.summary ?? []);
      await api.putUtility(p.utility);
      autoSaved.current = p.sig;
      flash("✓ 已自动保存", 1500);
    } catch (e) {
      flashErr(`自动保存失败：${errText(e)}`, 5000);
    }
  };

  useEffect(() => {
    if (autoSaved.current === null) { autoSaved.current = queueSig; return; } 
    if (autoSaved.current === queueSig) return;  
    pending.current = {
      sig: queueSig,
      queues: draft.queues,
      utility: draft.utility ?? EMPTY_UTILITY,
    };
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => { void flush(); }, delayMs);
    
  }, [queueSig, delayMs]);

  
  useEffect(() => () => { void flush(); }, []); 

  return { flush };
}
