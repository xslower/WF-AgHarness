
import type { PluginConfigField } from "../../api";
import { MASKED_PLUGIN_SECRET } from "../../api";
import { usePluginConfig } from "./usePluginConfig";
import { useFlash } from "../useFlash";

interface Props {
  pluginId: string;
  
  project: string;
  onSaved?: () => void;
}

export function PluginConfigForm({ pluginId, project, onSaved }: Props) {
  const c = usePluginConfig(pluginId, project, onSaved);
  const { msg, flash } = useFlash(3000);

  if (c.error && !c.fields.length) return <div className="err-badge">{c.error}</div>;
  if (!c.loaded) return <div className="dim pad8">加载中…</div>;
  if (!c.fields.length) return <div className="dim pad8">该插件没有可配置项</div>;

  const submit = async () => {
    if (await c.save()) flash("✓ 配置已保存");
  };

  return (
    <div className="plugin-config">
      {c.fields.map((f) => (
        <label key={f.key} className="plugin-config-row">
          <span className="plugin-config-label" title={f.key}>
            {f.label}
            {f.required && <em className="req">*</em>}
          </span>
          <Field field={f} value={c.values[f.key]}
            onChange={(v) => c.setValue(f.key, v)} />
        </label>
      ))}
      {c.error && <div className="err-badge" style={{ whiteSpace: "pre-wrap" }}>{c.error}</div>}
      <div className="row" style={{ marginTop: 8 }}>
        <button onClick={() => void submit()} disabled={c.busy}>
          {c.busy ? "保存中…" : "保存配置"}
        </button>
        {msg && <span className="dim">{msg}</span>}
        <span className="dim" style={{ marginLeft: "auto", fontSize: 11 }}
          title="配置值加密存在系统 agent.db；插件用 plugin.config(name) 读取">
          加密保存在系统 agent.db（密钥加密）
        </span>
      </div>
    </div>
  );
}

function Field({ field, value, onChange }: {
  field: PluginConfigField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const common = {
    placeholder: field.placeholder
      ?? (field.type === "secret" || field.type === "key" ? "已设置则不显示" : ""),
  };
  switch (field.type) {
    case "text":
      return <textarea {...common} rows={3} value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)} />;
    case "number":
      return <input type="number" {...common} min={field.min} max={field.max}
        value={value === "" || value === undefined ? "" : Number(value)}
        onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} />;
    case "boolean":
      return (
        <input type="checkbox" checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)} />
      );
    case "select":
      return (
        <select value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}>
          <option value="">（未选）</option>
          {(field.options ?? []).map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      );
    case "secret":
    case "key": {
      const masked = value === MASKED_PLUGIN_SECRET;
      return (
        <input type="password" {...common}
          value={masked ? "" : String(value ?? "")}
          placeholder={masked ? MASKED_PLUGIN_SECRET + "（已设置，留空不改）" : common.placeholder}
          onChange={(e) => onChange(e.target.value)} />
      );
    }
    case "path":
    case "string":
    default:
      return <input {...common} value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)} />;
  }
}


export { Field as PluginFieldInput };
