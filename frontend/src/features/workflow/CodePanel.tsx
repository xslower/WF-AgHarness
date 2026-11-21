
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { javascript } from "@codemirror/lang-javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import { Icon } from "../../kernel/ui/icons";
import { PanelClose } from "./PanelClose";

interface Props {
  selDsl: Record<string, string> | null;
  jsonText: string;
  onJsonChange: (v: string) => void;
  onJsonDirty: () => void;
  onPatch: (key: string, value: string) => void;
  onApply: () => void;
  onReset: () => void;
  
  onClose?: () => void;
}

export function CodePanel({ selDsl, jsonText, onJsonChange, onJsonDirty, onPatch, onApply, onReset, onClose }: Props) {
  return (
    <div className="wf-code">
      {onClose && <PanelClose onClose={onClose} title="收起代码区" />}
      {selDsl && selDsl.type === "code" ? (
        <>
          <div className="palette-title"><Icon name="file-text" /> 节点代码 · {selDsl.id}（{selDsl.lang || "python"}）</div>
          <div className="wf-cm-wrap">
            <CodeMirror
              value={selDsl.code ?? ""}
              theme={oneDark}
              extensions={selDsl.lang === "node" ? [javascript()] : [python()]}
              basicSetup={{ autocompletion: true, lineNumbers: true, foldGutter: true }}
              onChange={(v) => onPatch("code", v)} />
          </div>
          <div className="dim" style={{ fontSize: 11 }}>协议：\${"{"}inputs.x{"}"}/\${"{"}节点id{"}"} 变量替换；stdout 即输出，下游用 \${selDsl.id} 引用</div>
        </>
      ) : (
        <>
          <div className="palette-title">📄 工作流 JSON</div>
          <textarea className="wf-editor" value={jsonText} spellCheck={false}
            onChange={(e) => { onJsonDirty(); onJsonChange(e.target.value); }} />
          <div className="wf-code-actions">
            <button className="primary" onClick={onApply}>应用到画布</button>
            <button onClick={onReset}>重置</button>
          </div>
        </>
      )}
    </div>
  );
}
