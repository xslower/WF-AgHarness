
import { useState } from "react";

import type { AppConfig } from "../../kernel/api";
import type { ThemeManifest } from "../../kernel/theme/contracts";
import { Modal } from "../../kernel/ui/Modal";
import type { QueueKind, SettingsTab } from "./modelEdit";
import { GeneralTab } from "./GeneralTab";
import { McpTab } from "./McpTab";
import { PluginsTab } from "./PluginsTab";
import { ProvidersTab } from "./ProvidersTab";
import { QueuesTab } from "./QueuesTab";
import { SkillsTab } from "./SkillsTab";
import { useProviderEditor } from "./useProviderEditor";
import { useQueueAutoSave } from "./useQueueAutoSave";
import { useSettingsDraft } from "./useSettingsDraft";

interface Props {
  config: AppConfig;
  onClose: () => void;
  onSaved: (c: AppConfig) => void;
  uiPluginId: string;
  setUiPluginId: (id: string) => void;
  themes: ThemeManifest[];
}

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "providers", label: "模型 Provider" },
  { id: "queues", label: "模型队列" },
  { id: "general", label: "通用" },
  { id: "plugins", label: "插件" },
  { id: "skills", label: "Skills" },
  { id: "mcp", label: "MCP" },
];

export function SettingsPanel({
  config, onClose, onSaved, uiPluginId, setUiPluginId, themes,
}: Props) {
  const [tab, setTab] = useState<SettingsTab>("providers");
  const draftCtl = useSettingsDraft(config, onSaved);
  const { draft, setDraft, adoptConfig, flash, flashErr, msg, saveSetting } = draftCtl;
  const provider = useProviderEditor(draftCtl);
  const { flush } = useQueueAutoSave(draft, flash, flashErr);

  const toggleQueue = (kind: QueueKind, spec: string) => {
    setDraft((d) => {
      const q = [...d.queues[kind]];
      const i = q.indexOf(spec);
      if (i >= 0) q.splice(i, 1); else q.push(spec);
      return { ...d, queues: { ...d.queues, [kind]: q } };
    });
  };

  const moveQueue = (kind: QueueKind, i: number, dir: -1 | 1) => {
    setDraft((d) => {
      const q = [...d.queues[kind]];
      const j = i + dir;
      if (j < 0 || j >= q.length) return d;
      [q[i], q[j]] = [q[j], q[i]];
      return { ...d, queues: { ...d.queues, [kind]: q } };
    });
  };

  return (
    <Modal
      tabs={TABS} tab={tab} onTab={setTab}
      onClose={() => { void flush(); onClose(); }}
      subtitle={<span className="flash-icon" title={msg || ""}
        style={{ visibility: msg ? "visible" : "hidden" }}>✓</span>}
      flash={msg ? { text: msg, err: msg.startsWith("✗") } : null}
    >
      {tab === "providers" && (
        <ProvidersTab
          draft={draft} setDraft={setDraft} flash={flash} adoptConfig={adoptConfig}
          provider={provider}
        />
      )}

      {tab === "queues" && (
        <QueuesTab
          draft={draft} setDraft={setDraft}
          tests={provider.tests} test={provider.test}
          toggleQueue={toggleQueue} moveQueue={moveQueue}
        />
      )}

      {tab === "plugins" && <PluginsTab />}

      {tab === "skills" && <SkillsTab />}

      {tab === "mcp" && <McpTab />}

      {tab === "general" && (
        <GeneralTab
          settings={draft.settings}
          saveSetting={saveSetting}
          uiPluginId={uiPluginId} setUiPluginId={setUiPluginId}
          themes={themes}
        />
      )}
    </Modal>
  );
}
