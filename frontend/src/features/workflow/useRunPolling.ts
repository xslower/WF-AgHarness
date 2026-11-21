
import { useCallback, useEffect, useRef } from "react";
import { api } from "../../kernel/api";
import type { WfRun } from "../../kernel/api";

const POLL_MS = 1000;

export interface Poller {
  
  start: (runId: string, project: string,
          onUpdate: (r: WfRun) => void, onDone: (r: WfRun) => void) => void;
  
  stop: () => void;
  
  timerRef: React.MutableRefObject<number | null>;
  
  pollingId: React.MutableRefObject<string | null>;
}

export function useRunPolling(): Poller {
  const timerRef = useRef<number | null>(null);
  
  const idRef = useRef<string | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    idRef.current = null;
  }, []);

  
  useEffect(() => stop, [stop]);

  const start = useCallback((
    runId: string,
    project: string,
    onUpdate: (r: WfRun) => void,
    onDone: (r: WfRun) => void,
  ) => {
    stop();      
    timerRef.current = window.setInterval(async () => {
      const r = await api.wfRunStatus(runId, project).catch(() => null);
      if (!r) return;
      onUpdate(r);
      if (r.status === "running") return;
      stop();
      onDone(r);
    }, POLL_MS);
    idRef.current = runId;
  }, [stop]);

  return { start, stop, timerRef, pollingId: idRef };
}
