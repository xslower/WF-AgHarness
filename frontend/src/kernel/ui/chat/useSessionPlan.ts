
import { useCallback, useState } from "react";

import { patchPrefs, readPrefs, type SessionPrefs } from "../../chat/sessionPrefs";


export const DEFAULT_PLAN_ON = false;

export interface PlanSelection {
  on: boolean;
  setOn: (v: boolean) => void;
}

export function useSessionPlan(opts: {
  
  outerPrefs: SessionPrefs | undefined;
  outerSet: ((v: boolean) => void) | undefined;
  activeSid: string | null;
}): PlanSelection {
  const { outerPrefs, outerSet, activeSid } = opts;
  const defaultOn = DEFAULT_PLAN_ON;
  const [inner, setInner] = useState(
    () => (readPrefs(activeSid).plan ?? (defaultOn ? "1" : "0")) === "1");
  const [innerSid, setInnerSid] = useState(activeSid);
  
  if (activeSid !== innerSid) {
    setInnerSid(activeSid);
    setInner((readPrefs(activeSid).plan ?? (defaultOn ? "1" : "0")) === "1");
  }

  const writeInner = useCallback((v: boolean) => {
    setInner(v);
    patchPrefs(activeSid, { plan: v ? "1" : "0" });
  }, [activeSid]);

  return {
    
    on: outerPrefs !== undefined
      ? (outerPrefs.plan ?? (defaultOn ? "1" : "0")) !== "0"
      : inner,
    setOn: outerSet ?? writeInner,
  };
}
