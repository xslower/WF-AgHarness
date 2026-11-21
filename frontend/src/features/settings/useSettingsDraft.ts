
import { useCallback, useRef, useState, type Dispatch, type SetStateAction } from "react";

import { api } from "../../kernel/api";
import type { AppConfig, Settings } from "../../kernel/api";
import { cloneConfig } from "./modelEdit";
import { errText } from "../../kernel/ui/errText";
import { useFlash } from "../../kernel/ui/useFlash";

export interface SettingsDraft {
  draft: AppConfig;
  setDraft: Dispatch<SetStateAction<AppConfig>>;
  
  adoptConfig: (c: AppConfig) => void;
  
  reload: () => Promise<void>;
  
  saveSetting: (key: keyof Settings, value: Settings[keyof Settings]) => Promise<void>;
  msg: string;
  flash: (text: string, ms?: number) => void;
  
  flashErr: (text: string, ms?: number) => void;
}

export function useSettingsDraft(
  config: AppConfig,
  onSaved: (c: AppConfig) => void,
): SettingsDraft {
  const [draft, setDraft] = useState<AppConfig>(() => cloneConfig(config));
  const { msg, flash, flashErr } = useFlash(6000);
  
  const saveSeq = useRef(0);

  const adoptConfig = useCallback((c: AppConfig) => {
    onSaved(c);
    setDraft(c);
  }, [onSaved]);

  const reload = useCallback(async () => {
    adoptConfig(await api.getConfig());
  }, [adoptConfig]);

  const saveSetting = useCallback(async (
    key: keyof Settings,
    value: Settings[keyof Settings],
  ) => {
    const seq = ++saveSeq.current;
    
    setDraft((d) => ({ ...d, settings: { ...d.settings, [key]: value } }));
    try {
      
      await api.putSettings({ [key]: value } as Partial<Settings>);
      const fresh = await api.getConfig();
      if (seq !== saveSeq.current) return;     
      adoptConfig(fresh);
      flash("✓ 已保存", 1500);
    } catch (e) {
      if (seq !== saveSeq.current) return;
      flashErr(`保存失败：${errText(e)}`);
      const fresh = await api.getConfig().catch(() => null);
      if (fresh && seq === saveSeq.current) adoptConfig(fresh);
    }
  }, [adoptConfig, flash, flashErr]);

  return { draft, setDraft, adoptConfig, reload, saveSetting, msg, flash, flashErr };
}
