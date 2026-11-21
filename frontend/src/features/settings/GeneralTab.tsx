
import type { ReactNode } from "react";

import type { Settings } from "../../kernel/api";
import type { ThemeManifest } from "../../kernel/theme/contracts";
import { InlineValue } from "../../kernel/ui/InlineValue";
import { EnvSection } from "./EnvSection";
import {
  SETTING_GROUPS, formatSetting, inlineKind, parseSetting, type SettingDef,
} from "./settingsFields";

interface Props {
  settings: Settings;
  saveSetting: (key: keyof Settings, value: Settings[keyof Settings]) => void;
  uiPluginId: string;
  setUiPluginId: (id: string) => void;
  themes: ThemeManifest[];
}

export function GeneralTab({ settings, saveSetting, uiPluginId, setUiPluginId, themes }: Props) {
  const commit = (def: SettingDef, raw: string) => {
    const value = parseSetting(def, raw);
    saveSetting(def.key, value);
    
    if (def.key === "notifyOnSessionDone" && value === true
        && typeof Notification !== "undefined" && Notification.permission === "default") {
      void Notification.requestPermission().catch(() => {  });
    }
  };

  return (
    <div className="panel settings-grid">
      <p className="dim">点击右侧的值即可编辑，失焦或回车自动保存，Esc 取消。</p>

      {SETTING_GROUPS.map((g) => (
        <section key={g.title} className="settings-group">
          <h4>{g.title}</h4>
          {g.fields.map((def) => {
            const raw = formatSetting(def, settings[def.key]);
            return (
              <SettingRow key={def.key} label={def.label} help={def.help}>
                {def.kind === "boolean" ? (
                  <button className={`settings-value bool ${raw === "true" ? "on" : "off"}`}
                    onClick={() => commit(def, raw === "true" ? "false" : "true")}>
                    {raw === "true" ? "✓ 已开启" : "✗ 已关闭"}
                  </button>
                ) : (
                  <InlineValue value={raw} onCommit={(v) => commit(def, v)}
                    kind={inlineKind(def)} options={def.options}
                    placeholder={def.placeholder} min={def.min}
                    title={def.help ? `${def.help}（点击编辑）` : "点击编辑"}
                    display={(v) => def.kind === "select"
                      ? ((def.options?.find((o) => o.value === v)?.label ?? v) || "（未设置）")
                      : (v || def.placeholder || "（空）")} />
                )}
              </SettingRow>
            );
          })}
        </section>
      ))}

      <section className="settings-group">
        <h4>外观</h4>
        <SettingRow label="界面主题" help="外置主题来自主题插件清单">
          <InlineValue kind="select" value={uiPluginId} onCommit={setUiPluginId}
            options={themes.map((t) => ({
              value: t.id, label: `${t.name}${t.source ? "（外置）" : ""}`,
            }))}
            display={(v) => themes.find((t) => t.id === v)?.name ?? v} />
        </SettingRow>
      </section>

      <EnvSection />
    </div>
  );
}

function SettingRow({ label, help, children }: {
  label: string; help?: string; children: ReactNode;
}) {
  return (
    <div className="settings-row" title={help}>
      <span className="settings-key">
        {label}{help && <span className="info" title={help}>ⓘ</span>}
      </span>
      <div className="settings-val">{children}</div>
    </div>
  );
}
