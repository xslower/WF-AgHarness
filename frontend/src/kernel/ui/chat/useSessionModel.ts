
import { useCallback, useState } from "react";

import { normalizeSpec } from "../../model/modelSpec";
import { patchPrefs, readPrefs } from "../../chat/sessionPrefs";

export interface ModelSelection {
  model: string;
  setModel: (v: string) => void;
  
  adopt: (v: string) => void;
}

export function useSessionModel(opts: {
  
  outerModel: string | undefined;
  outerSet: ((v: string) => void) | undefined;
  
  activeSid: string | null;
}): ModelSelection {
  const { outerModel, outerSet, activeSid } = opts;
  const [inner, setInner] = useState(
    () => normalizeSpec(readPrefs(activeSid).model));
  const [innerSid, setInnerSid] = useState(activeSid);
  
  if (activeSid !== innerSid) {
    setInnerSid(activeSid);
    setInner(normalizeSpec(readPrefs(activeSid).model));
  }

  const writeInner = useCallback((v: string) => {
    const spec = normalizeSpec(v);
    setInner(spec);
    patchPrefs(activeSid, { model: spec });
  }, [activeSid]);

  return {
    model: outerModel ?? inner,
    setModel: outerSet ?? writeInner,
    adopt: (v: string) => setInner(normalizeSpec(v)),
  };
}
