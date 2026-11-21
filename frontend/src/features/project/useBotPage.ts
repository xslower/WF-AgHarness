
import { useCallback, useEffect, useState } from "react";

import { api } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";

import type { PluginBotDecl } from "../../kernel/api/types";

export interface BotController {
  
  values: Record<string, unknown>;
  setValue: (key: string, v: unknown) => void;
  
  canCompose: boolean;
  
  composeIntoQuestion: () => Promise<void>;
  
  fillRequest: { text: string; seq: number } | undefined;
  error: string;
  reload: () => Promise<void>;
}

export function useBotPage(hostProject: string, pluginId: string,
                           bot: PluginBotDecl | null | undefined): BotController {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [fillRequest, setFillRequest] = useState<{ text: string; seq: number }>();
  const [error, setError] = useState("");
  
  useEffect(() => {
    const init: Record<string, unknown> = {};
    for (const f of bot?.inputs ?? []) {
      if (f.default !== undefined) init[f.key] = f.default;
    }
    setValues(init);
  }, [bot?.inputs]);

  const setValue = useCallback((key: string, v: unknown) => {
    setValues((prev) => ({ ...prev, [key]: v }));
  }, []);

  const inputs = bot?.inputs ?? [];
  const canCompose = inputs.filter((f) => f.required).every((f) => {
    const v = values[f.key];
    return v !== undefined && v !== null && String(v).trim() !== "";
  });

  const reload = useCallback(async () => {
    try {
      await api.projectOverview(hostProject);
      setError("");
    } catch (e) {
      setError(errText(e));
    }
  }, [hostProject]);

  const composeIntoQuestion = useCallback(async () => {
    
    try {
      const r = await api.pluginCompose(pluginId, hostProject, values);
      
      
      setFillRequest((prev) => ({ text: r.text, seq: (prev?.seq ?? 0) + 1 }));
      setError("");
    } catch (e) {
      setError(errText(e));
    }
  }, [pluginId, hostProject, values]);

  return { values, setValue, canCompose, composeIntoQuestion, fillRequest,
           error, reload };
}
