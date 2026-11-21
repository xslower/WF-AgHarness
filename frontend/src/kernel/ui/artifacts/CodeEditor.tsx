
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { javascript } from "@codemirror/lang-javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView } from "@codemirror/view";

interface Props {
  value: string;
  ext?: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
}

export function CodeEditor({ value, ext, onChange, onBlur }: Props) {
  return (
    <CodeMirror
      value={value}
      theme={oneDark}
      
      extensions={[ext === "py" ? python() : javascript(), EditorView.lineWrapping]}
      basicSetup={{ autocompletion: true, lineNumbers: true, foldGutter: true }}
      onChange={onChange}
      onBlur={onBlur} />
  );
}
