
import type { Dispatch, SetStateAction } from "react";
import { Icon } from "../../kernel/ui/icons";

interface Props {
  log: { q: string; ok: boolean; note: string }[];
  input: string;
  setInput: Dispatch<SetStateAction<string>>;
  busy: boolean;
  onSend: () => void;
}

export function AssistPanel({ log, input, setInput, busy, onSend }: Props) {
  return (
    <div className="wf-chat">
      <div className="palette-title"><Icon name="robot" /> AI 辅助开发</div>
      <div className="assist-log">
        {log.length === 0 && <div className="dim">输入指令让 LLM 修改工作流（增删节点、改连线、改字段），结果先应用到画布，确认后点保存。LLM 失败时可在左侧代码区手改 JSON。</div>}
        {log.map((l, i) => (
          <div key={i} className={l.ok ? "assist-item ok" : "assist-item err"}>
            <div className="assist-q">{l.q}</div>
            <div className="dim">{l.note}</div>
          </div>
        ))}
      </div>
      <div className="assist-input-row">
        <input value={input} disabled={busy}
          placeholder={busy ? "LLM 处理中…" : "如：在 s1 后加一个 OCR 节点识别 ${inputs.img}"}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") onSend(); }} />
        <button className="primary" onClick={onSend} disabled={busy || !input.trim()}>发送</button>
      </div>
    </div>
  );
}
