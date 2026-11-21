
import { useCallback, useEffect } from "react";
import type { Edge, Node } from "@xyflow/react";

import type { NodeCatalogItem, WfAvailable, WfRun, WfRunSummary, WorkflowDef } from "../../kernel/api";
import { dslToCanvas } from "./dsl";
import { workflowPersistence } from "./workflowPersistence";
import { useDiskSync, useRunSync } from "./useEditorSync";
import { useEditorLoad } from "./useEditorLoad";
import type { SaveState } from "./useAutoSave";
import type { useAutoSave } from "./useAutoSave";


const AUTOSAVE_DEBOUNCE_MS = 1500;

export interface EditorLifecycleDeps {
  project: string;
  name: string;
  wf: WorkflowDef | null;
  setWf: (w: WorkflowDef | null) => void;
  setParallelMode: (m: "agent" | "sequential") => void;
  setInputVals: (v: Record<string, string>) => void;
  setSelId: (v: string | null) => void;
  setNameEdit: (v: string | null) => void;
  setCatalog: (v: NodeCatalogItem[] | null) => void;
  setAvailable: (v: WfAvailable[]) => void;
  setSaveState: (upd: SaveState | ((s: SaveState) => SaveState)) => void;
  setRfNodes: (n: Node[]) => void;
  setRfEdges: (e: Edge[]) => void;
  rfNodes: Node[];
  rfEdges: Edge[];
  parallelMode: "agent" | "sequential";
  idCounter: { current: number };
  runGen: { current: number };
  draftRef: { current: WorkflowDef | null };
  timerRef: { current: number | null };
  runRef: { current: WfRun | null };
  saveState: SaveState;
  flash: (t: string, ms?: number) => void;
  onChanged: () => void;
  
  onRunChanged: () => void;
  autosave: ReturnType<typeof useAutoSave>;
  
  selfSaveAt: { current: number };
  run: WfRun | null;
  refreshHistory: (project: string, wfName?: string) => Promise<WfRunSummary[]>;
  openRun: (rid: string, project: string) => Promise<void>;
}

export function useEditorLifecycle(d: EditorLifecycleDeps) {
  const {
    savedNameRef, lastSavedRef, lastRevRef, loadedRef, saveKey, doSave, saveErr: _err,
  } = d.autosave;
  const store = workflowPersistence();

  
  const loadFromDisk = useCallback(async (remote = false) => {
    if (!d.name) return;
    const w = await store.fetch(d.name, d.project);
    d.setWf(w);
    savedNameRef.current = w.name;
    d.setParallelMode(w.parallel_mode === "agent" ? "agent" : "sequential");
    d.setInputVals(Object.fromEntries((w.inputs ?? []).map((i: { name: string }) => [i.name, ""])));
    const { nodes, edges } = dslToCanvas(w);
    d.setRfNodes(nodes);
    d.setRfEdges(edges);
    d.idCounter.current = w.nodes.length;
    lastSavedRef.current = saveKey(w, nodes, edges,
      w.parallel_mode === "agent" ? "agent" : "sequential");
    lastRevRef.current = String(w._revision || "");
    loadedRef.current = true;
    if (remote) d.flash("✓ 已同步磁盘上的最新版本");
  }, [d.name, d.project, saveKey, d.flash, d.setRfNodes, d.setRfEdges,
      d.setWf, d.setParallelMode, d.setInputVals, d.idCounter,
      savedNameRef, lastSavedRef, lastRevRef, loadedRef, store]);

  
  useDiskSync({
    name: d.name, project: d.project, wfName: d.wf?.name ?? d.name,
    savedName: savedNameRef, lastRev: lastRevRef, loaded: loadedRef,
    saveState: d.saveState, flash: d.flash, reload: loadFromDisk,
    selfSaveAt: d.selfSaveAt,
  });

  
  useRunSync({
    name: d.name, project: d.project, savedName: savedNameRef, runRef: d.runRef,
    refreshHistory: d.refreshHistory, openRun: d.openRun, run: d.run,
    onRunChanged: d.onRunChanged, flash: d.flash,
  });

  
  useEditorLoad({
    name: d.name, project: d.project, projectForRuns: d.project, gen: d.runGen,
    draft: d.draftRef,
    savedName: savedNameRef, lastSaved: lastSavedRef, loaded: loadedRef,
    idCounter: d.idCounter, timerRef: d.timerRef,
    setWf: d.setWf, setSelId: d.setSelId, setNameEdit: d.setNameEdit,
    setCatalog: d.setCatalog, setAvailable: d.setAvailable, setInputVals: d.setInputVals,
    setSaveState: d.setSaveState, setRfNodes: d.setRfNodes, setRfEdges: d.setRfEdges,
    loadFromDisk, refreshHistory: d.refreshHistory, openRun: d.openRun,
    saveKey, flash: d.flash,
  });

  
  const save = useCallback(async (): Promise<boolean> => {
    const savedWf = await doSave(d.wf, d.rfNodes, d.rfEdges, d.parallelMode);
    if (savedWf) d.selfSaveAt.current = Date.now();   
    if (savedWf && d.wf && (savedWf.name !== d.wf.name || savedWf._revision !== d.wf._revision
        || savedWf.parallel_mode !== d.wf.parallel_mode)) {
      d.setWf(savedWf);
    }
    return savedWf !== null;
  }, [doSave, d.wf, d.rfNodes, d.rfEdges, d.parallelMode, d.setWf, d.selfSaveAt]);

  
  useEffect(() => {
    if (!d.wf || !loadedRef.current) return;
    const key = saveKey(d.wf, d.rfNodes, d.rfEdges, d.parallelMode);
    if (key === lastSavedRef.current) return;
    d.setSaveState((s) => (s === "saving" ? s : "dirty"));
    const t = window.setTimeout(() => { void save(); }, AUTOSAVE_DEBOUNCE_MS);
    return () => window.clearTimeout(t);
    
  }, [d.rfNodes, d.rfEdges, d.wf]);

  return { loadFromDisk, save };
}
