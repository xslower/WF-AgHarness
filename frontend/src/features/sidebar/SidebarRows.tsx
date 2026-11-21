
import { useMemo, useState } from "react";

import type { SessionSummary, WorkflowSummary } from "../../kernel/api";
import type { Attn } from "../../kernel/attention/attn";
import { readStored, writeStored } from "../../kernel/ui/useLocalState";
import { fmtStamp } from "../../kernel/ui/format";
import { Icon } from "../../kernel/ui/icons";
import { AttnBadges } from "./AttnBadges";



export interface SessionRowProps {
  s: SessionSummary;
  active: boolean;
  renaming: { id: string; value: string } | null;
  onStartRename: (s: SessionSummary) => void;
  onRenameChange: (value: string) => void;
  onRenameCommit: (sid: string, value: string) => void;
  onRenameCancel: () => void;
  
  onOpenMenu: (e: React.MouseEvent<HTMLElement>, sid: string) => void;
  menu: { id: string; x: number; y: number } | null;
  onCloseMenu: () => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  attn: Attn;
}

export function SessionRow(p: SessionRowProps) {
  const { s } = p;
  return (
    <div className={`session-item ${p.active ? "active" : ""}`}
      onClick={() => { p.onCloseMenu(); p.onOpen(s.id); }}>
      {p.renaming?.id === s.id ? (
        <div className="sess-rename-row" onClick={(e) => e.stopPropagation()}>
          <input autoFocus value={p.renaming.value}
            onChange={(e) => p.onRenameChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") p.onRenameCommit(s.id, p.renaming!.value);
              if (e.key === "Escape") p.onRenameCancel();
            }} />
          <button className="primary" title="确认重命名"
            onClick={() => p.onRenameCommit(s.id, p.renaming!.value)}>✓</button>
        </div>
      ) : (
        <>
          <div className="session-title">
            <Icon name="chat" />
            <span className="sess-name">{s.title}</span>
            {}
            <AttnBadges attn={p.attn} />
          </div>
          <div className="session-meta">
            {fmtStamp(s.created_at)}
            <button className="link" title="会话操作" onClick={(e) => p.onOpenMenu(e, s.id)}>⋮</button>
          </div>
          {p.menu?.id === s.id && (
            <div className="sess-menu" style={{ left: p.menu.x, top: p.menu.y }}
              onClick={(e) => e.stopPropagation()}>
              <button onClick={() => { p.onStartRename(s); p.onCloseMenu(); }}>
                <Icon name="pencil" /> 重命名
              </button>
              <button className="danger" onClick={() => { p.onCloseMenu(); p.onDelete(s.id); }}>
                <Icon name="trash" /> 删除
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}




function useOpenGroups() {
  const [open, setOpen] = useState<Set<string>>(() => new Set(readStored<string[]>("ui.wfGroupsOpen", [])));
  const toggle = (name: string) => {
    setOpen((prev) => {
      const n = new Set(prev);
      if (n.has(name)) n.delete(name); else n.add(name);
      writeStored("ui.wfGroupsOpen", [...n]);
      return n;
    });
  };
  return { open, toggle };
}

export interface FlowTreeProps {
  project: string;
  flows: WorkflowSummary[];
  
  activeName: string | null;
  onOpen: (project: string, name: string) => void;
  onReparent: (project: string, name: string, parent: string) => Promise<void>;
  attnOfFlow: (project: string, name: string) => Attn;
}


export function FlowTree(p: FlowTreeProps) {
  const { open, toggle } = useOpenGroups();
  const [drag, setDrag] = useState<{ project: string; name: string } | null>(null);
  const [dropOn, setDropOn] = useState<string | null>(null);

  
  const tops = useMemo(
    () => p.flows.filter((w) => !w.parent || !p.flows.some((x) => x.name === w.parent)),
    [p.flows]);

  const endDrag = () => { setDrag(null); setDropOn(null); };

  const renderRow = (w: WorkflowSummary, depth: number): React.ReactNode => {
    const kids = p.flows.filter((x) => x.parent === w.name);
    const isOpen = open.has(w.name);
    return (
      <div key={w.name}>
        <div
          className={`session-item flow-item ${p.activeName === w.name ? "active" : ""} ${dropOn === w.name ? "drop-target" : ""}`}
          style={{ "--depth": depth } as React.CSSProperties}
          draggable
          onDragStart={(e) => { setDrag({ project: p.project, name: w.name }); e.dataTransfer.effectAllowed = "move"; }}
          onDragOver={(e) => { if (drag && drag.name !== w.name) { e.preventDefault(); setDropOn(w.name); } }}
          onDragLeave={() => setDropOn((d) => (d === w.name ? null : d))}
          onDrop={(e) => {
            e.preventDefault(); e.stopPropagation();
            if (drag && drag.name !== w.name) void p.onReparent(drag.project, drag.name, w.name);
            endDrag();
          }}
          onClick={() => p.onOpen(p.project, w.name)}>
          <div className="session-title">
            {kids.length > 0 ? (
              <span className="proj-toggle" onClick={(e) => { e.stopPropagation(); toggle(w.name); }}>
                {isOpen ? "▾" : "▸"}
              </span>
            ) : <span className="proj-toggle">·</span>}
            <Icon name="workflow" />
            <span className="sess-name">{w.name}</span>
            {}
            <AttnBadges attn={p.attnOfFlow(p.project, w.name)} />
          </div>
        </div>
        {kids.length > 0 && isOpen && kids.map((k) => renderRow(k, depth + 1))}
      </div>
    );
  };

  return (
    <>
      {tops.map((w) => renderRow(w, 0))}
      <div className="flow-drop-root" title="拖到这里移出分组"
        onDragOver={(e) => { if (drag) e.preventDefault(); }}
        onDrop={(e) => {
          e.preventDefault();
          if (drag && drag.project === p.project && drag.name) void p.onReparent(p.project, drag.name, "");
          endDrag();
        }} />
    </>
  );
}
