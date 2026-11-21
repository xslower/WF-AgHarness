
import { useEffect, useState } from "react";

import { api } from "../../api";
import type { PluginConfigField, PluginConfigResponse } from "../../api";
import { errText } from "../errText";


function merged(fields: PluginConfigField[], values: Record<string, unknown>) {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    const v = values[f.key];
    out[f.key] = v !== undefined ? v : (f.default ?? "");
  }
  return out;
}

export interface PluginConfigController {
  fields: PluginConfigField[];
  values: Record<string, unknown>;
  setValue: (key: string, v: unknown) => void;
  error: string;
  busy: boolean;
  loaded: boolean;
  save: () => Promise<boolean>;
}

export function usePluginConfig(
  pluginId: string,
  project: string,
  onSaved?: () => void,
): PluginConfigController {
  const [fields, setFields] = useState<PluginConfigField[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError("");
    api.pluginConfigGet(pluginId, project)
      .then((r: PluginConfigResponse) => {
        if (cancelled) return;
        setFields(r.fields);
        setValues(merged(r.fields, r.values));
        setLoaded(true);
      })
      .catch((e: unknown) => { if (!cancelled) setError(errText(e)); });
    return () => { cancelled = true; };
  }, [pluginId, project]);

  const setValue = (key: string, v: unknown) =>
    setValues((s) => ({ ...s, [key]: v }));

  const save = async (): Promise<boolean> => {
    setBusy(true);
    setError("");
    try {
      const r = await api.pluginConfigPut(pluginId, values, project);
      
      setValues(merged(r.fields, r.values));
      onSaved?.();
      return true;
    } catch (e) {
      setError(errText(e));
      return false;
    } finally {
      setBusy(false);
    }
  };

  return { fields, values, setValue, error, busy, loaded, save };
}
