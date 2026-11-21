
import { ChatPanel } from "../../kernel/ui/chat/ChatPanel";
import { PluginFieldInput } from "../../kernel/ui/plugins/PluginConfigForm";
import { Icon } from "../../kernel/ui/icons";
import { useBotPage } from "./useBotPage";
import { usePluginDetail } from "./usePluginDetail";

interface Props {
  hostProject: string;
  pluginId: string;
  onBack: () => void;
}

export function BotPage({ hostProject, pluginId, onBack }: Props) {
  
  const detail = usePluginDetail(hostProject, pluginId);
  const plugin = detail.plugin;
  const bot = plugin?.bot;
  const c = useBotPage(hostProject, pluginId, bot);
  const title = bot?.title || plugin?.name || pluginId;

  return (
    <div className="projhome botpage">
      <header className="projhome-head">
        <div className="projhome-title">
          <button className="icon-btn" title="返回项目主页" onClick={onBack}>
            <Icon name="x" />
          </button>
          <h2>{title}</h2>
          <span className="projhome-badge">{bot?.workflow ? "工作流" : "对话"}</span>
        </div>
        <div className="projhome-actions">
          <button onClick={() => void c.reload()}>刷新</button>
        </div>
        {c.error && <div className="projhome-err-inline">{c.error}</div>}
      </header>

      {bot?.greeting && (
        <div className="projhome-hint botpage-greeting">{bot.greeting}</div>
      )}

      {(bot?.inputs?.length ?? 0) > 0 && (
        <section className="projhome-sec botpage-inputs">
          <h3>输入</h3>
          {bot!.inputs!.map((f) => (
            <label key={f.key} className="plugin-config-row">
              <span className="plugin-config-label" title={f.key}>
                {f.label}{f.required && <em className="req">*</em>}
              </span>
              <PluginFieldInput field={f} value={c.values[f.key]}
                onChange={(v) => c.setValue(f.key, v)} />
            </label>
          ))}
          <div className="row" style={{ marginTop: 8 }}>
            {}
            <button disabled={!c.canCompose} onClick={() => void c.composeIntoQuestion()}>
              填入问题
            </button>
            <span className="dim" style={{ marginLeft: "auto", fontSize: 11 }}>
              拼好的问题会填进下方输入框，可在那里再改后发送
            </span>
          </div>
        </section>
      )}

      <section className="projhome-sec botpage-chat">
        <ChatPanel
          project={hostProject}
          storeKey={`bot.${hostProject}.${pluginId}`}
          sessionMeta={{ kind: "bot", origin: pluginId }}
          title=""
          compact
          workflow={bot?.workflow || ""}
          fillRequest={c.fillRequest}
        />
      </section>
    </div>
  );
}
