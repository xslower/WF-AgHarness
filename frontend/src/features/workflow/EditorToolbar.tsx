
import { Icon } from "../../kernel/ui/icons";
import { baseName } from "../../kernel/ui/format";


export type PanelKey = "palette" | "code" | "chat" | "inspector" | "log" | "llm";


export interface PanelOpenState {
  palette?: boolean;
  code?: boolean;
  chat?: boolean;
  inspector?: boolean;
  log?: boolean;
}

export interface EditorToolbarProps {
  project: string;
  wfName: string;
  
  nameEdit: string | null;
  setNameEdit: (v: string | null) => void;
  onConfirmName: () => void;
  parallelMode: "agent" | "sequential";
  onParallelChange: (mode: "agent" | "sequential") => void;
  parallelMenu: boolean;
  setParallelMenu: (open: boolean) => void;
  saveState: string;
  saveErr: string;
  onSave: () => void;
  onExport: () => void;
  onImportClick: () => void;
  onAddLlmNode: () => void;
  onToggle: (panel: PanelKey) => void;
  
  logOpen?: boolean;
  
  runLogOpen?: boolean;
  
  panelOpen?: PanelOpenState;
  onDelete: () => void;
  onRun: () => void;
  running: boolean;
  
  status?: string;
  
  onTogglePublish?: () => void;

  
  runProject?: string;
  runProjects?: string[];
  onRunProjectChange?: (p: string) => void;
}

function saveLabel(state: string, err: string): string {
  if (state === "saved") return "● 已保存";
  if (state === "saving") return "○ 保存中…";
  if (state === "dirty") return `○ 待保存${err ? "：" + err : ""}`;
  return `✗ 保存失败：${err}`;
}

export function EditorToolbar(p: EditorToolbarProps) {
  return (
    <div className="wf-toolbar">
      <>
        <button onClick={p.onImportClick} title="导入工作流 JSON（模型自动适配）"><Icon name="import" /> 导入</button>
        <button onClick={p.onExport} title="导出工作流 JSON"><Icon name="export" /> 导出</button>
      </>
      {p.nameEdit === null ? (
        <span className="wf-name" title="点击工作流名称可重命名">
          {p.project ? baseName(p.project) : "全局"} -{" "}
          <span className="wf-name-edit" onClick={() => p.setNameEdit(p.wfName)}>
            {p.wfName || "未命名工作流"}
          </span>
        </span>
      ) : (
        <>
          <input className="wf-name" autoFocus value={p.nameEdit}
            placeholder="工作流名称"
            onChange={(e) => p.setNameEdit(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") p.onConfirmName();
              if (e.key === "Escape") p.setNameEdit(null);
            }} />
          <button className="primary" title="确认名称" onClick={p.onConfirmName}>✓</button>
        </>
      )}
      <span className="dim wf-parallel" title="并行执行方式（点击修改）"
        onClick={() => p.setParallelMenu(true)}>
        并行：{p.parallelMode === "agent" ? "真并行（子任务）" : "顺序（后一路等待）"} ▾
      </span>
      {p.parallelMenu && (
        <div className="wf-ctxmenu wf-parallel-menu" style={{ position: "relative", left: 0, top: 0 }}
          onMouseLeave={() => p.setParallelMenu(false)}>
          <button className={p.parallelMode === "sequential" ? "cur" : ""} onClick={() => {
            p.onParallelChange("sequential"); p.setParallelMenu(false);
          }}>顺序（后一路等待）</button>
          <button className={p.parallelMode === "agent" ? "cur" : ""} onClick={() => {
            p.onParallelChange("agent"); p.setParallelMenu(false);
          }}>真并行（子任务）</button>
        </div>
      )}
      <span className="flex1" />
      <span className="dim" title={p.saveErr || undefined}>
        {saveLabel(p.saveState, p.saveErr)}
      </span>
      <button className="primary" onClick={p.onSave} title="立即保存">💾</button>
      {p.onTogglePublish && (
        <button className={(p.status || "draft") === "published" ? "on" : ""}
          onClick={p.onTogglePublish}
          title={(p.status || "draft") === "published"
            ? "撤回发布：从全局主页移除" : "发布：在全局主页列出（草稿不列）"}>
          {(p.status || "draft") === "published" ? "已发布" : "发布"}
        </button>
      )}

      {}
      {!p.panelOpen?.palette && (
        <button onClick={() => p.onToggle("palette")} title="节点列表"><Icon name="puzzle" /></button>
      )}
      {!p.panelOpen?.code && (
        <button onClick={() => p.onToggle("code")} title="代码（JSON 编辑）">📄</button>
      )}
      {!p.panelOpen?.chat && (
        <button onClick={() => p.onToggle("chat")} title="AI 对话"><Icon name="robot" /></button>
      )}
      {!p.panelOpen?.inspector && (
        <button onClick={() => p.onToggle("inspector")} title="属性面板"><Icon name="settings" /></button>
      )}
      {!p.panelOpen?.log && (
        <button onClick={() => p.onToggle("log")}
          title="运行日志（本次运行的节点输出/耗时/产出）"><Icon name="list" /></button>
      )}
      {!p.logOpen && (
        <button onClick={() => p.onToggle("llm")}
          title="LLM 会话记录（双击画布节点可直接看该节点对话）"><Icon name="robot" /></button>
      )}
      <button className="danger" onClick={p.onDelete} title="删除当前工作流（需确认）"><Icon name="trash" /></button>
      <button className="primary run-btn" onClick={p.onRun} disabled={p.running}>
        ▶ {p.running ? "运行中" : "启动"}
      </button>
    </div>
  );
}

