
import {
  ReactFlow, Background, Controls, MiniMap,
  type Node, type Edge, type OnNodesChange, type OnEdgesChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { AppConfig, WfAvailable, WfRun, WfRunFile, WfRunSummary,
  WorkflowDef } from "../../kernel/api";
import { CODE_TEMPLATE, Palette, type PaletteItem } from "./Palette";
import { PaletteItemsContext, type FlowNodeData } from "./dsl";
import { nodeTypes } from "./DslNode";
import { Inspector } from "./Inspector";
import { CodePanel } from "./CodePanel";
import { WorkflowChat } from "./WorkflowChat";
import { RunLogPanel, useLogHeight } from "./RunPanel";
import { RunFilesViewer } from "./RunFilesViewer";
import { resizeHeight } from "../../kernel/ui/drag";

export interface EditorPanels {
  palette: boolean;
  code: boolean;
  chat: boolean;
  inspector: boolean;
  log: boolean;
}

export interface EditorBodyProps {
  project: string;
  
  scope: string;
  
  name: string;
  wf: WorkflowDef;
  items: PaletteItem[];
  nodes: Node[];
  edges: Edge[];
  onNodesChange: OnNodesChange<Node>;
  onEdgesChange: OnEdgesChange<Edge>;
  onConnect: (c: { source?: string | null; target?: string | null }) => void;
  selDsl: Record<string, string> | null;
  insVars: string[];
  available: WfAvailable[];
  run: WfRun | null;
  history: WfRunSummary[];
  viewFile: WfRunFile | null;
  setViewFile: (f: WfRunFile | null) => void;
  jsonText: string;
  setJsonText: (t: string) => void;
  setJsonDirty: () => void;
  applyJson: () => void;
  resetJson: () => void;
  width: { codeW: number; chatW: number; insW: number };
  setWidth: {
    setCodeW: (n: number) => void;
    setChatW: (n: number) => void;
    setInsW: (n: number) => void;
  };
  panelDrag: (set: (n: number) => void, cur: number, min: number,
              max: number) => (e: React.MouseEvent) => void;
  show: EditorPanels;
  
  onClosePanel: (panel: "palette" | "code" | "chat" | "inspector" | "log") => void;
  onAddNode: (item: PaletteItem) => void;
  onCreateCode: (code: string) => void;
  onNodeClick: (id: string, data: FlowNodeData) => void;
  
  onNodeDoubleClick?: (id: string) => void;
  onPaneClick: () => void;
  onNodeContextMenu: (e: React.MouseEvent, n: Node) => void;
  onPatch: (key: string, value: string) => void;
  onDeleteSelected: () => void;
  onOpenWorkflow: (name: string) => void;
  onTestRun: () => void;
  onRunFrom: () => void;
  onExtract: () => void;
  onCancel: () => void;
  onResume: () => void;
  onHuman: (choice: string, comment: string) => void;
  
  onRedo?: (nodeId: string) => void;
  
  why?: React.ReactNode;
  onOpenRun: (rid: string) => void;
  
  session?: string;
  config?: AppConfig | null;
  onNewSession?: () => void;
  onPickSession?: (sid: string) => void;
}

export function EditorBody(p: EditorBodyProps) {
  const [logH, setLogH] = useLogHeight(p.scope);
  const { panelDrag, width, setWidth } = p;
  return (
    <>
      <div className="wf-ide" style={{ "--wf-code-w": width.codeW + "px",
        "--wf-chat-w": width.chatW + "px",
        "--wf-ins-w": width.insW + "px" } as React.CSSProperties}>
        {p.show.palette && (
          <Palette items={p.items} onAdd={p.onAddNode}
            onClose={() => p.onClosePanel("palette")}
            onCreateCode={() => p.onCreateCode(CODE_TEMPLATE)} />
        )}

        {}
        <div className="wf-canvas">
          <PaletteItemsContext.Provider value={p.items}>
            <ReactFlow
              nodes={p.nodes} edges={p.edges}
              onNodesChange={p.onNodesChange} onEdgesChange={p.onEdgesChange}
              onConnect={p.onConnect as never}
              onNodeClick={(_, n) => p.onNodeClick(n.id, n.data as FlowNodeData)}
              onNodeDoubleClick={(_, n) => p.onNodeDoubleClick?.(n.id)}
              onPaneClick={p.onPaneClick}
              onNodeContextMenu={p.onNodeContextMenu}
              nodeTypes={nodeTypes}
              fitView deleteKeyCode={["Delete", "Backspace"]}
              defaultEdgeOptions={{ type: "smoothstep" }}
            >
              <Background gap={18} />
              <MiniMap pannable zoomable />
              <Controls />
            </ReactFlow>
          </PaletteItemsContext.Provider>
        </div>

        {}
        {p.show.inspector && (
          <>
            <div className="wf-edge" title="拖动调节属性面板宽度"
              onMouseDown={panelDrag(setWidth.setInsW, width.insW, 220, 560)}>
              <span className="art-drag-bar" />
            </div>
            <Inspector selDsl={p.selDsl} items={p.items} run={p.run} onPatch={p.onPatch}
              onClose={() => p.onClosePanel("inspector")}
              onDelete={p.onDeleteSelected} vars={p.insVars}
              available={p.available}
              onOpenWorkflow={p.onOpenWorkflow}
              onTestRun={p.onTestRun}
              onRunFrom={p.onRunFrom}
              onExtract={p.onExtract} />
          </>
        )}

        {}
        {p.show.code && (
          <>
            <div className="wf-edge" title="拖动调节代码区宽度"
              onMouseDown={panelDrag(setWidth.setCodeW, width.codeW, 260, 760)}>
              <span className="art-drag-bar" />
            </div>
            <CodePanel
              selDsl={p.selDsl}
              onClose={() => p.onClosePanel("code")}
              jsonText={p.jsonText}
              onJsonChange={p.setJsonText}
              onJsonDirty={p.setJsonDirty}
              onPatch={p.onPatch}
              onApply={p.applyJson}
              onReset={p.resetJson} />
          </>
        )}

        {}
        {p.show.chat && (
          <>
            <div className="wf-edge" title="拖动调节 AI 面板宽度"
              onMouseDown={panelDrag(setWidth.setChatW, width.chatW, 240, 680)}>
              <span className="art-drag-bar" />
            </div>
            <WorkflowChat project={p.project} name={p.wf.name || p.name}
              onClose={() => p.onClosePanel("chat")} />
          </>
        )}
      </div>

      {}
      {p.show.log && (
        <div className="wf-log-row">
          <RunLogPanel run={p.run} history={p.history} height={logH}
            onClose={() => p.onClosePanel("log")}
            onResizeStart={resizeHeight({ height: logH, min: 120, max: 640,
              edge: "top", setHeight: setLogH })}
            openFile={p.viewFile?.path ?? null}
            onOpenFile={p.setViewFile}
            onCancel={p.onCancel}
            onResume={p.onResume}
            onHuman={p.onHuman}
            onRedo={p.onRedo}
            why={p.why}
            onOpenRun={p.onOpenRun} />
          <RunFilesViewer file={p.viewFile} onClose={() => p.setViewFile(null)} />
        </div>
      )}
    </>
  );
}
