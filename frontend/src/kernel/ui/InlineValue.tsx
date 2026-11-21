
import { useRef, useState, type ReactNode } from "react";

export interface InlineOption { value: string; label: string }

export interface InlineValueProps {
  value: string;
  onCommit: (raw: string) => void;
  
  display?: (raw: string) => ReactNode;
  kind?: "text" | "number" | "select" | "lines";
  options?: InlineOption[];
  placeholder?: string;
  emptyText?: string;
  chipClass?: string;
  inputClass?: string;
  min?: number;
  rows?: number;
  title?: string;
}

export function InlineValue(p: InlineValueProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  
  const done = useRef(false);

  const open = () => { done.current = false; setDraft(p.value); setEditing(true); };
  const cancel = () => { done.current = true; setEditing(false); };
  const commit = (raw: string) => {
    if (done.current) return;
    done.current = true;
    setEditing(false);
    
    if (raw === p.value) return;
    p.onCommit(raw);
  };

  if (!editing) {
    return (
      <span className={p.chipClass ?? "settings-value"} role="button" tabIndex={0}
        title={p.title ?? "点击编辑"}
        onClick={open}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
        }}>
        {p.display ? p.display(p.value) : (p.value || p.emptyText || "（空）")}
        <span className="edit-hint">✎</span>

      </span>
    );
  }

  
  const change = (e: { target: { value: string } }) => setDraft(e.target.value);
  const keys = (e: { key: string; ctrlKey: boolean; metaKey: boolean;
                     preventDefault: () => void }) => {
    if (e.key === "Escape") { e.preventDefault(); cancel(); }
    else if (e.key === "Enter" && (p.kind !== "lines" || e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      commit(draft);
    }
  };
  const cls = p.inputClass ?? "settings-input";

  if (p.kind === "select") {
    return (
      <select className={cls} autoFocus data-kind="select" value={draft}
        onChange={(e) => commit(e.target.value)}
        onBlur={(e) => commit(e.target.value)} onKeyDown={keys}>
        {(p.options ?? []).map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    );
  }
  if (p.kind === "lines") {
    return (
      <textarea className={cls} autoFocus data-kind="lines" rows={p.rows ?? 3}
        placeholder={p.placeholder} value={draft} onChange={change}
        onBlur={(e) => commit(e.target.value)} onKeyDown={keys} />
    );
  }
  return (
    <input className={cls} autoFocus data-kind={p.kind ?? "text"}
      type={p.kind === "number" ? "number" : "text"} min={p.min}
      placeholder={p.placeholder} value={draft} onChange={change}
      onBlur={(e) => commit(e.target.value)} onKeyDown={keys} />
  );
}
