
import { useCallback, useEffect, useState } from "react";

import { api } from "../../api";
import type { ProjectPolicy } from "../../api";
import { patchPrefs, readPolicyPref } from "../../chat/sessionPrefs";

export interface ProjectPolicyController {
  policy: ProjectPolicy | null;
  
  mode: string;
  change: (mode: string) => void;
  
  reload: () => Promise<void>;
}

export function useProjectPolicy(sessionId: string | null): ProjectPolicyController {
  const [policy, setPolicy] = useState<ProjectPolicy | null>(null);
  
  const [chosen, setChosen] = useState(() => readPolicyPref(sessionId));

  
  const reload = useCallback(async () => {
    try {
      setPolicy(await api.projectPolicy(""));
    } catch {
      setPolicy(null);
    }
  }, []);
  useEffect(() => { void reload(); }, [reload]);

  
  useEffect(() => { setChosen(readPolicyPref(sessionId)); }, [sessionId]);

  const change = useCallback((mode: string) => {
    setChosen(mode);
    patchPrefs(sessionId, { policy: mode });
  }, [sessionId]);

  return {
    policy,
    mode: chosen || policy?.default || "workspace",
    change,
    reload,
  };
}
