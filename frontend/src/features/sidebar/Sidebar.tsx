
import { memo, useMemo, useState } from "react";

import type {
  AppConfig, ProjectNode, SessionSummary, WorkflowSummary,
} from "../../kernel/api";
import { collectPaths } from "../../kernel/project/projectTree";
import type { AppView } from "../../kernel/app/view";
import type { Attn } from "../../kernel/attention/attn";
import { DirPicker } from "./DirPicker";
import { ProjectTree } from "./ProjectTree";
import { SessionRow } from "./SidebarRows";
import { useSidebarActions, groupByProject } from "./useSidebarActions";
import { useSidebarMenus } from "./useSidebarMenus";
import { useSidebarWidth } from "./useSidebarWidth";
import { useProjectDrag } from "./useProjectDrag";
import { Icon } from "../../kernel/ui/icons";

interface Props {
  sessions: SessionSummary[];
  projTree: ProjectNode | null;
  wfs: Record<string, WorkflowSummary[]>;
  expanded: Set<string>;
  curProject: string;
  curId: string | null;
  view: AppView;
  
  scope: string;
  config: AppConfig | null;
  
  onShowUsage: () => void;
  onExpand: (path: string) => void;
  onToggleExpand: (path: string) => void;
  onToggleAll: () => void;
  onOpenProject: (path: string) => void;
  
  
  onOpenPlugin: (project: string, id: string) => void;
  onOpenSession: (id: string) => void;
  onOpenWorkflow: (project: string, name: string) => void;
  onNewSession: (id: string, project: string) => void;
  onDeleteSession: (id: string) => void;
  onOpenSettings: () => void;
  onOpenGlobalWorkflows: () => void;
  
  onOpenHome: () => void;

  refreshSessions: () => Promise<void>;
  refreshTree: () => Promise<void>;
  refreshWfs: (project: string) => Promise<void>;
  
  attnOf: (sid: string) => Attn;
  
  attnOfFlow: (project: string, name: string) => Attn;
}


function SidebarImpl({
  sessions, projTree, wfs, expanded, curProject, curId, view, scope, config, onShowUsage,
  onExpand, onToggleExpand, onToggleAll, onOpenProject, onOpenPlugin, onOpenSession, onOpenWorkflow,
  onNewSession, onDeleteSession, onOpenSettings, onOpenGlobalWorkflows, onOpenHome,
  refreshSessions, refreshTree, refreshWfs,
  attnOf, attnOfFlow,
}: Props) {
  
  const [dirPicker, setDirPicker] = useState<{ base?: string } | null>(null);
  const {
    sessMenu, projMenu, setSessMenu, setProjMenu, openSessMenu, openProjMenu,
  } = useSidebarMenus();
  const [renaming, setRenaming] = useState<{ id: string; value: string } | null>(null);
  
  const [unGroupedOpen, setUnGroupedOpen] = useState(true);
  const { sidebarW, onSidebarDrag } = useSidebarWidth(scope);

  const actions = useSidebarActions({
    wfs, refreshSessions, refreshTree, refreshWfs,
    onExpand, onNewSession, onOpenWorkflow,
  });

  
  const projectDrag = useProjectDrag(actions.moveProject);

  const sessionsByProject = useMemo(() => groupByProject(sessions), [sessions]);
  const allExpanded = useMemo(
    () => !!projTree && collectPaths(projTree).every((p) => expanded.has(p)),
    [projTree, expanded]);
  
  
  const unGrouped = useMemo(
    () => sessions.filter((s) => !s.project && !s.kind), [sessions]);

  const commitRename = async (sid: string, value: string) => {
    setRenaming(null);
    await actions.renameSession(sid, value);
  };

  const renderSession = (s: SessionSummary) => (
    <SessionRow key={s.id} s={s}
      active={view.kind === "chat" && s.id === curId}
      attn={attnOf(s.id)}
      renaming={renaming}
      onStartRename={(x) => setRenaming({ id: x.id, value: x.title })}
      onRenameChange={(v) => setRenaming((r) => (r ? { ...r, value: v } : r))}
      onRenameCommit={(id, v) => void commitRename(id, v)}
      onRenameCancel={() => setRenaming(null)}
      onOpenMenu={openSessMenu} menu={sessMenu} onCloseMenu={() => setSessMenu(null)}
      onOpen={onOpenSession} onDelete={onDeleteSession} />
  );

  
  const confirmDir = async (path: string) => {
    const base = dirPicker?.base;
    if (await actions.registerProject(path)) {
      if (base) onExpand(base);
      setDirPicker(null);
    }
  };

  return (
    <aside className="sidebar" style={{ width: sidebarW }}>
      <div className="sidebar-head">
        <div className="brand" title="回到全局主页" onClick={onOpenHome}
          style={{ cursor: "pointer" }}>WF-AgHarness</div>
        <div className="row gap4">
          <button className="icon-btn" title="选择本地目录注册为项目" onClick={() => setDirPicker({})}>
            <Icon name="folder-open" />
          </button>
          <button className="icon-btn" onClick={onToggleAll}
            title={allExpanded ? "全部收起" : "全部展开"}><Icon name="expand" /></button>
          <button className="icon-btn" onClick={onOpenGlobalWorkflows} title="全局工作流">
            <Icon name="workflow" />
          </button>
          <button className="icon-btn" onClick={onOpenSettings}><Icon name="settings" /></button>
        </div>
      </div>

      <div className={`session-list ${projectDrag.dragging ? "proj-dragging" : ""}`}
        onDragOver={(e) => { if (e.target === e.currentTarget) projectDrag.onDragOver(e, ""); }}
        onDrop={(e) => { if (e.target === e.currentTarget) projectDrag.onDrop(e, ""); }}>
        {projectDrag.dragging && (
          <div className="dim proj-drop-root">拖到这里 = 移回一级项目</div>
        )}
        {projTree && projTree.children.length > 0
          ? projTree.children.map((c) => (
            <ProjectTree key={c.path} node={c}
              hostProject={c.path}
              expanded={expanded} curProject={curProject}
              activeFlow={view.kind === "workflow" ? view.name : null}
              sessionsByProject={sessionsByProject} wfs={wfs}
              projMenu={projMenu} attnOf={attnOf} attnOfFlow={attnOfFlow}
              onToggleExpand={onToggleExpand} onOpenProject={onOpenProject}
              onOpenPlugin={onOpenPlugin} onOpenWorkflow={onOpenWorkflow}
              onOpenProjMenu={openProjMenu}
              onCloseProjMenu={() => setProjMenu(null)}
              onAddSubProject={(parent) => setDirPicker({ base: parent })}
              onAddTask={(p) => void actions.addTask(p)}
              onAddFlow={(p) => void actions.addFlow(p)}
              onRemoveProject={(p) => { setProjMenu(null); void actions.removeProject(p); }}
              onReparentFlow={actions.setFlowParent}
              drag={projectDrag}
              renderSession={renderSession} />
          ))
          : <div className="dim pad8">还没有项目：点右上角文件夹按钮选择本地目录注册；项目内可在 ⋮ 菜单添加子项目</div>}

        {unGrouped.length > 0 && (
          <div className="proj-node ungrouped-node">
            <div className="proj-row">
              <span className="proj-toggle" onClick={() => setUnGroupedOpen((v) => !v)}>
                {unGroupedOpen ? "▾" : "▸"}
              </span>
              <span className="proj-name"
                title="没有归属项目的会话：历史数据，或新建时未选择项目">
                <Icon name="folder" /> 未分组
              </span>
              <span className="proj-ops dim">{unGrouped.length}</span>
            </div>
            {unGroupedOpen && <div className="proj-children">{unGrouped.map(renderSession)}</div>}
          </div>
        )}
      </div>

      {}
      <div className="queue-info">
        <button className="link" onClick={onShowUsage} title="查看 token 与费用用量">
          📊 用量
        </button>
      </div>
      <div className="sidebar-edge" onMouseDown={onSidebarDrag} title="拖动调节侧栏宽度">
        <span className="art-drag-bar" />
      </div>

      {dirPicker && (
        <DirPicker key={dirPicker.base || "__root__"} base={dirPicker.base}
          onClose={() => setDirPicker(null)} onConfirm={confirmDir} />
      )}
    </aside>
  );
}


export const Sidebar = memo(SidebarImpl);
