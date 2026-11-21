
import { useEffect } from "react";

import { Icon } from "../../kernel/ui/icons";
import { WorkflowEditor } from "./WorkflowEditor";
import { useGlobalWorkflows } from "./useGlobalWorkflows";

interface Props {
  onBack: () => void;
  
  onOpenWorkflow: (project: string, name: string) => void;
}

export function GlobalWorkflowsPanel({ onBack, onOpenWorkflow }: Props) {
  const c = useGlobalWorkflows();
  const { refresh } = c;

  useEffect(() => { void refresh(); }, [refresh]);

  if (c.openName !== null) {
    return (
      <WorkflowEditor
        project=""
        name={c.openName}
        onBack={() => { c.setOpenName(null); void refresh(); }}
        onChanged={() => { void refresh(); }}
        onOpenWorkflow={onOpenWorkflow}
      />
    );
  }

  return (
    <div className="orch-panel">
      <div className="orch-topbar">
        <button className="icon-btn" title="返回" onClick={onBack}>←</button>
        <span className="orch-title">全局工作流</span>
        <span className="dim">所有项目可引用</span>
        <span className="flex1" />
        <button className="primary" disabled={c.creating}
          onClick={() => void c.create()}>{c.creating ? "创建中…" : "+ 新建"}</button>
      </div>

      {c.error && <div className="error">✗ {c.error}</div>}

      <div className="orch-body">
        <div className="orch-list">
          {c.list.length === 0 ? (
            <div className="dim pad8">暂无全局工作流，点击「新建」创建</div>
          ) : c.list.map((s) => (
            <GlobalFlowRow key={s.name} s={s}
              onOpen={() => c.setOpenName(s.name)}
              onTogglePublish={() => void c.togglePublish(s)}
              onRemove={() => void c.remove(s.name)} />
          ))}
        </div>
        <div className="orch-detail">
          <div className="dim pad8">点击左侧工作流进入画布编辑；这里的保存都落在全局目录，项目里可通过「工作流」下拉或子工作流节点引用。</div>
        </div>
      </div>
    </div>
  );
}

function GlobalFlowRow({ s, onOpen, onTogglePublish, onRemove }: {
  s: import("../../kernel/api").WorkflowSummary;
  onOpen: () => void;
  onTogglePublish: () => void;
  onRemove: () => void;
}) {
  const published = (s.status || "draft") === "published";
  return (
    <div className="orch-item" onClick={onOpen}>
      <div className="orch-item-name"><Icon name="workflow" /> {s.name}</div>
      <div className="orch-item-meta">
        {s.nodes} 节点{s.desc ? ` · ${s.desc}` : ""}
        {published && <span className="projhome-badge project">已发布</span>}
        <button className="link"
          title={published ? "取消发布：从全局主页移除" : "发布：在全局主页列出"}
          onClick={(e) => { e.stopPropagation(); onTogglePublish(); }}>
          {published ? "撤回" : "发布"}
        </button>
        <button className="link del"
          onClick={(e) => { e.stopPropagation(); onRemove(); }}>删</button>
      </div>
    </div>
  );
}
