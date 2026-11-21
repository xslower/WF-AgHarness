
import type { ProjectNode, SessionSummary, WorkflowSummary } from "../../kernel/api";
import type { Attn } from "../../kernel/attention/attn";
import { Icon } from "../../kernel/ui/icons";
import { FlowTree } from "./SidebarRows";
import type { ProjectDragState } from "./useProjectDrag";

export interface ProjectTreeProps {
  node: ProjectNode;
  expanded: Set<string>;
  curProject: string;
  
  activeFlow: string | null;
  
  hostProject: string;
  sessionsByProject: Map<string, SessionSummary[]>;
  wfs: Record<string, WorkflowSummary[]>;
  projMenu: { path: string; x: number; y: number } | null;
  attnOf: (sid: string) => Attn;
  attnOfFlow: (project: string, name: string) => Attn;

  onToggleExpand: (path: string) => void;
  onOpenProject: (path: string) => void;
  
  onOpenPlugin: (project: string, id: string) => void;
  onOpenWorkflow: (project: string, name: string) => void;
  onOpenProjMenu: (e: React.MouseEvent<HTMLElement>, path: string) => void;
  onCloseProjMenu: () => void;
  onAddSubProject: (parent: string) => void;
  onAddTask: (project: string) => void;
  onAddFlow: (project: string) => void;
  onRemoveProject: (path: string) => void;
  onReparentFlow: (project: string, name: string, parent: string) => Promise<void>;
  
  drag: ProjectDragState;
  renderSession: (s: SessionSummary) => React.ReactNode;
}

export function ProjectTree(p: ProjectTreeProps) {
  const node = p.node;
  const isOpen = p.expanded.has(node.path);
  const tasks = p.sessionsByProject.get(node.path) ?? [];
  
  
  const flows = node.pluginProject ? [] : (p.wfs[node.path] ?? []);
  const menuOpen = p.projMenu?.path === node.path;

  
  const item = (fn: () => void) => () => { p.onCloseProjMenu(); fn(); };

  
  
  const hasContent = tasks.length > 0 || flows.length > 0 || node.children.length > 0;

  return (
    <div className="proj-node">
      <div
        className={`proj-row ${p.curProject === node.path ? "active" : ""} ${p.drag.dropOn === node.path ? "drop-target" : ""}`}
        draggable
        onDragStart={(e) => p.drag.onDragStart(e, node.path)}
        onDragOver={(e) => p.drag.onDragOver(e, node.path)}
        onDragLeave={() => p.drag.onDragLeave(node.path)}
        onDrop={(e) => p.drag.onDrop(e, node.path)}
        onDragEnd={p.drag.onDragEnd}
        title={`${node.path}（点击进入项目主页；可拖动到其它项目上调整归属）`}>
        <span className="proj-toggle"
          onClick={hasContent ? () => p.onToggleExpand(node.path) : undefined}>
          {hasContent ? (isOpen ? "▾" : "▸") : "·"}
        </span>
        <span className="proj-name"
          title={`${node.path}（${node.pluginProject ? "点击进入插件页面" : "点击进入项目主页"}）`}
          onClick={() => node.pluginProject
            ? p.onOpenPlugin(p.hostProject, node.pluginId || node.name)
            : p.onOpenProject(node.path)}>
          <Icon name={node.pluginProject ? "puzzle" : "folder"} /> {node.name}
        </span>
        <span className="proj-ops">
          <button className={`icon-btn ${menuOpen ? "on" : ""}`} title="更多操作"
            onClick={(e) => p.onOpenProjMenu(e, node.path)}>⋮</button>
        </span>
      </div>

      {menuOpen && (
        <div className="sess-menu" style={{ left: p.projMenu!.x, top: p.projMenu!.y }}
          onClick={(e) => e.stopPropagation()}>
          <button onClick={item(() => p.onAddTask(node.path))}>
            <Icon name="chat" /> 新建任务
          </button>
          {node.depth < 3 && (
            <button onClick={item(() => p.onAddSubProject(node.path))}>
              <Icon name="folder" /> 添加子项目
            </button>
          )}
          <button onClick={item(() => p.onAddFlow(node.path))}>
            <Icon name="workflow" /> 创建工作流
          </button>
          <div className="sess-menu-sep" />
          <button className="danger" onClick={item(() => p.onRemoveProject(node.path))}>
            <Icon name="trash" /> 删除项目
          </button>
        </div>
      )}

      {isOpen && (
        <div className="proj-children">
          {}
          {}
          {node.children.map((c) => (
            <ProjectTree key={c.path} {...p} hostProject={p.hostProject} node={c} />
          ))}
          {tasks.map(p.renderSession)}
          {!node.pluginProject && (
            <FlowTree project={node.path} flows={flows} activeName={p.activeFlow}
              onOpen={p.onOpenWorkflow} onReparent={p.onReparentFlow}
              attnOfFlow={p.attnOfFlow} />
          )}
        </div>
      )}
    </div>
  );
}
