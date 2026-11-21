
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  type Node, type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "../../kernel/api";
import type { NodeCatalogItem, WfAvailable, WfRun, WfRunFile, WorkflowDef } from "../../kernel/api";
import { events } from "../../kernel/api/eventBridge";
import { CODE_TEMPLATE, Palette, catalogToItems, type PaletteItem } from "./Palette";
import { PaletteItemsContext, dslToCanvas, type FlowNodeData } from "./dsl";
import { nodeTypes } from "./DslNode";
import { Inspector } from "./Inspector";
import { CodePanel } from "./CodePanel";
import { EditorToolbar } from "./EditorToolbar";
import { isRunning } from "./runEntries";
import { WorkflowChat } from "./WorkflowChat";
import { RunInputDialog, RunLogPanel } from "./RunPanel";
import { RunFilesViewer } from "./RunFilesViewer";
import { useAutoSave } from "./useAutoSave";
import { EditorBody } from "./EditorBody";
import { useCanvasOps } from "./useCanvasOps";
import { useWorkflowIO } from "./useWorkflowIO";
import { usePanelLayout } from "./usePanelLayout";
import { useWorkflowRun } from "./useWorkflowRun";
import { LlmSessionDrawer } from "./LlmSessionLog";
import { useEditorLifecycle } from "./useEditorLifecycle";
import { makeWorkflowCommands } from "./workflowCommands";
import { workflowPersistence } from "./workflowPersistence";
import { makeRunEntries } from "./runEntries";
import { useRunWhy } from "./useRunWhy";
import { RunWhyPanel } from "./RunWhyPanel";
import { togglePanel, type PanelSetters } from "./panelToggles";
import { usePanelVisibility } from "./usePanelVisibility";
import { useEditorUiState } from "./useEditorUiState";
import { useLlmLogDrawer } from "./useLlmLogDrawer";
import { deleteWorkflow } from "./editorActions";
import { Icon } from "../../kernel/ui/icons";
import { useFlash } from "../../kernel/ui/useFlash";

import { resizeHeight } from "../../kernel/ui/drag";

interface Props {
  project: string;
  name: string;
  onBack: () => void;
  onChanged: () => void;
  
  onOpenWorkflow?: (project: string, name: string) => void;
}

export function WorkflowEditor({ project, name, onBack, onChanged,
                                 onOpenWorkflow }: Props) {
  const [wf, setWf] = useState<WorkflowDef | null>(null);
  const [inputVals, setInputVals] = useState<Record<string, string>>({});
  
  const ui = useEditorUiState();
  const { selId, setSelId, nameEdit, setNameEdit, parallelMenu, setParallelMenu, ctxMenu, setCtxMenu } = ui;
  
  
  const wfScope = `wf:${project || "global"}/${name}`;
  const { show, setVisible, apply: applyPanels, setters: panelSetters } = usePanelVisibility(wfScope);
  const [runAsk, setRunAsk] = useState(false);
  const [parallelMode, setParallelMode] = useState<"agent" | "sequential">("sequential");
  
  const log = useLlmLogDrawer(wfScope);
  const [catalog, setCatalog] = useState<NodeCatalogItem[] | null>(null);
  
  const [available, setAvailable] = useState<WfAvailable[]>([]);
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const idCounter = useRef(0);
  
  const selfSaveAtRef = useRef(0);
  
  const projectForRuns = project;
  
  const runGenRef = useRef(0);

  
  const { msg, setMsg, flash } = useFlash(4000);

  
  const {
    saveState, setSaveState, saveErr, setSaveErr,
    savedNameRef, lastSavedRef, lastRevRef, loadedRef, saveKey, doSave,
  } = useAutoSave({ project, onChanged });
  const { run, setRun, timerRef, startRun: hookStartRun,
    runSingleNode: hookRunSingleNode, startRunFrom: hookStartRunFrom, redoRun,
    history, refreshHistory, cancelRun, resumeRun, openRun, decideHuman } = useWorkflowRun();
  
  const whyCtl = useRunWhy(run?.id ?? "", projectForRuns);
  const { session, setSession } = log;
  
  const runRef = useRef<WfRun | null>(null);
  runRef.current = run;
  const { codeW, setCodeW, chatW, setChatW, insW, setInsW, panelDrag } = usePanelLayout(wfScope);
  
  
  const [viewFile, setViewFile] = useState<WfRunFile | null>(null);
  const {
    jsonText, setJsonText, jsonDirty, applyJson, resetJson,
    importRef, onImportFile, doExport,
  } = useWorkflowIO({
    wf, setWf, rfNodes, rfEdges, setRfNodes, setRfEdges,
    idCounter, project, flash, onChanged, setInputVals,
  });

  
  
  const draftRef = useRef<WorkflowDef | null>(null);

  
  const items = useMemo<PaletteItem[]>(() => catalogToItems(catalog), [catalog]);

  
  const { save } = useEditorLifecycle({
    project, name, wf, setWf, setParallelMode, setInputVals, setSelId, setNameEdit,
    setCatalog, setAvailable, setSaveState: setSaveState as never, setRfNodes, setRfEdges,
    rfNodes, rfEdges, parallelMode,
    idCounter, runGen: runGenRef, draftRef, timerRef, runRef,
    saveState, flash, onChanged,
    onRunChanged: () => setViewFile(null),
    autosave: { saveState, setSaveState, saveErr, setSaveErr,
      savedNameRef, lastSavedRef, lastRevRef, loadedRef, saveKey, doSave },
    selfSaveAt: selfSaveAtRef,
    run, refreshHistory, openRun,
  });

  
  useEffect(() => {
    if (!run) return;
    setRfNodes((ns) => ns.map((n) => ({
      ...n,
      data: { ...(n.data as FlowNodeData), status: run.nodes[n.id]?.status },
    })));
  }, [run, setRfNodes]);

  
  const selNode = rfNodes.find((n) => n.id === selId) ?? null;
  const selDsl = selNode ? (selNode.data as FlowNodeData).dsl as Record<string, string> : null;
  
  const insVars = useMemo(() => [
    ...(wf?.inputs ?? []).map((i) => `inputs.${i.name}`),
    ...rfNodes.map((n) => n.id),
    "prev",
  ], [wf, rfNodes]);

  const {
    addNode, addLlmNode, createCodeNode, onConnect, patchDsl,
    deleteSelected, deleteNode, copyNode, doExtract,
  } = useCanvasOps({
    rfNodes, rfEdges, setRfNodes, setRfEdges, selId, setSelId, idCounter,
    items, available, setAvailable, project,
    wfName: wf?.name ?? "",
    flash, onChanged,
    onCodeNodeCreated: () => applyPanels({ code: true, inspector: false, chat: true }),
  });

  
  const { startRun, runSingleNode, startRunFrom } = makeRunEntries({
    wfName: wf?.name ?? "", projectForRuns, project, inputVals, parallelMode,
    selId, flash, save,
  }, {
    startRun: hookStartRun, runSingleNode: hookRunSingleNode,
    startRunFrom: hookStartRunFrom,
  });

  const doDelete = () => deleteWorkflow({
    name: wf?.name ?? "", project, flash,
    stopAutosave: () => { loadedRef.current = false; },
    onChanged, onBack,
  });

  
  const cmd = makeWorkflowCommands({
    project, wf, savedName: savedNameRef, lastSaved: lastSavedRef,
    save, setWf, setInputVals: setInputVals as never, setRunAsk, setNameEdit,
    pendingName: nameEdit,
    startRun, flash, onChanged, onOpenWorkflow, available,
    lastRev: lastRevRef,
    saveKeyOf: (w) => saveKey(w ?? wf!, rfNodes, rfEdges, parallelMode),
  });

  


  if (!wf) return <div className="wf-page"><div className="dim pad8">加载中…</div></div>;

  return (
    <div className="wf-page no-pad">
      <EditorToolbar
        project={project} wfName={wf.name}
        nameEdit={nameEdit} setNameEdit={setNameEdit}
        onConfirmName={() => void cmd.confirmName()}
        parallelMode={parallelMode}
        onParallelChange={(m) => { setParallelMode(m); setWf({ ...wf, parallel_mode: m }); }}
        parallelMenu={parallelMenu} setParallelMenu={setParallelMenu}
        saveState={saveState} saveErr={saveErr}
        onSave={() => void save()}
        onExport={() => void doExport()}
        onImportClick={() => importRef.current?.click()}
        onAddLlmNode={addLlmNode}
        onToggle={(panel) => {
          if (panel === "llm") { log.setOpen(!log.open); return; }
          togglePanel(panel, panelSetters);
        }}
        logOpen={log.open}
        runLogOpen={show.log}
        panelOpen={show}
        
        status={project === "" ? String((wf as { status?: string }).status || "draft") : undefined}
        onTogglePublish={project === "" ? () => void cmd.togglePublish() : undefined}
        onDelete={() => void doDelete()}
        onRun={cmd.doRun}
        running={isRunning(run)}
      />
      <input ref={importRef} type="file" accept=".json,application/json" hidden onChange={(e) => { onImportFile(e.target.files); e.target.value = ""; }} />
      {msg && <div className="notice pad-h">{msg}</div>}
      {saveState === "error" && (
        <div className="notice pad-h" style={{ cursor: "pointer" }} onClick={save} title="点击重试保存">
          ✗ 保存失败：{saveErr}（点击重试）
        </div>
      )}

      {}
      {ctxMenu && (
        <div className="wf-ctxmenu" style={{ left: ctxMenu.x, top: ctxMenu.y }}
          onMouseLeave={() => setCtxMenu(null)}>
          <button onClick={() => { copyNode(ctxMenu.id); setCtxMenu(null); }}>⧉ 复制节点</button>
          <button className="danger" onClick={() => { deleteNode(ctxMenu.id); setCtxMenu(null); }}><Icon name="trash" /> 删除节点</button>
        </div>
      )}

      <RunInputDialog
        open={runAsk}
        inputs={wf.inputs ?? []}
        values={inputVals}
        setValues={setInputVals}
        onCancel={() => setRunAsk(false)}
        onStart={() => { setRunAsk(false); startRun(); }}
      />

      {log.open && (
        <LlmSessionDrawer
          project={projectForRuns}
          workflow={wf.name || name}
          config={null}
          run={run}
          selected={session}
          focusNode={log.focusNode}
          onNewSession={() => setSession("new")}
          onPickSession={(sid) => setSession(sid)}
          onClose={() => log.setOpen(false)}
          maximized={log.maximized}
          onToggleMax={() => log.setMaximized(!log.maximized)}
          width={log.width}
          onWidth={log.setWidth}
        />
      )}

      <EditorBody
        scope={wfScope}
        project={project}
        name={name}
        wf={wf}
        items={items}
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        selDsl={selDsl}
        insVars={insVars}
        available={available}
        run={run}
        history={history}
        viewFile={viewFile}
        setViewFile={setViewFile}
        jsonText={jsonText}
        setJsonText={setJsonText}
        setJsonDirty={() => { jsonDirty.current = true; }}
        applyJson={applyJson}
        resetJson={resetJson}
        width={{ codeW, chatW, insW }}
        setWidth={{ setCodeW, setChatW, setInsW }}
        panelDrag={panelDrag}
        show={show}
        onClosePanel={(panel) => setVisible(panel, false)}
        onAddNode={addNode}
        onCreateCode={(code) => createCodeNode(code)}
        onNodeClick={(id: string, data: FlowNodeData) => {
          setSelId(id);
          
          const dsl = data.dsl as Record<string, string>;
          if (dsl.type === "code") applyPanels({ code: true, inspector: false });
          else applyPanels({ inspector: true, code: false });
        }}
        onNodeDoubleClick={log.openAt}
        onPaneClick={ui.dismissPopups}
        onNodeContextMenu={(e, n) => {
          e.preventDefault();
          ui.openNodeMenu(e.clientX, e.clientY, n.id);
        }}
        onPatch={patchDsl}
        onDeleteSelected={deleteSelected}
        onOpenWorkflow={cmd.openSubWorkflow}
        onTestRun={() => void runSingleNode()}
        onRunFrom={() => void startRunFrom()}
        onExtract={() => void doExtract()}
        onCancel={() => void cancelRun({ project: projectForRuns, flash })}
        onResume={() => void resumeRun({ project: projectForRuns, flash })}
        onHuman={(choice, comment) =>
          void decideHuman({ project: projectForRuns, choice, comment, flash })}
        session={session}
        config={null}
        onNewSession={() => setSession("new")}
        onPickSession={(sid) => setSession(sid)}
        onOpenRun={(rid) => { void (async () => {
          
          await openRun(rid, projectForRuns, { onError: flash });
        })(); }}
        onRedo={(nid) => { void redoRun({ nodeId: nid, project: projectForRuns, flash }); }}
        why={<RunWhyPanel wf={whyCtl} runId={run?.id ?? ""}
          onRedo={(nid) => { void redoRun({ nodeId: nid, project: projectForRuns, flash }); }} />}

      />
    </div>
  );
}
