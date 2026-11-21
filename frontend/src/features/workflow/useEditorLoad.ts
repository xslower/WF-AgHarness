
import { useEffect, type MutableRefObject } from "react";
import type { Node, Edge } from "@xyflow/react";
import { api } from "../../kernel/api";
import type { NodeCatalogItem, WfAvailable, WorkflowDef } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import type { SaveState } from "./useAutoSave";
import { dslToCanvas } from "./dsl";
import { newWorkflow } from "./defaultWorkflow";


const DRAFT: WorkflowDef = newWorkflow();

export interface LoadArgs {
  name: string;
  project: string;
  projectForRuns: string;
  gen: MutableRefObject<number>;
  draft: MutableRefObject<WorkflowDef | null>;
  savedName: MutableRefObject<string>;
  lastSaved: MutableRefObject<string>;
  loaded: MutableRefObject<boolean>;
  idCounter: MutableRefObject<number>;
  timerRef: MutableRefObject<number | null>;
  setWf: (w: WorkflowDef | null) => void;
  setSelId: (id: string | null) => void;
  setNameEdit: (v: string | null) => void;
  setCatalog: (v: NodeCatalogItem[] | null) => void;
  setAvailable: (v: WfAvailable[]) => void;
  setInputVals: (v: Record<string, string>) => void;
  setSaveState: (s: SaveState) => void;
  setRfNodes: (n: Node[]) => void;
  setRfEdges: (e: Edge[]) => void;
  loadFromDisk: () => Promise<void>;
  refreshHistory: (project: string, wfName?: string) => Promise<{ id: string }[]>;
  openRun: (rid: string, project: string,
            opts?: { keepPolling?: boolean }) => Promise<void>;
  saveKey: (wf: WorkflowDef, nodes: Node[], edges: Edge[],
            mode: "agent" | "sequential") => string;
  flash: (t: string) => void;
}


export function useEditorLoad(a: LoadArgs): void {
  const {
    name, project, projectForRuns, gen, draft, savedName, lastSaved, loaded,
    idCounter, timerRef, setWf, setSelId, setNameEdit, setCatalog, setAvailable,
    setInputVals, setSaveState, setRfNodes, setRfEdges, loadFromDisk,
    refreshHistory, openRun, saveKey, flash,
  } = a;

  useEffect(() => {
    setWf(null);
    setSelId(null);
    setNameEdit(null);
    
    api.workflowNodes().then(setCatalog).catch(() => setCatalog(null));
    
    api.wfAvailable(project).then(setAvailable).catch(() => setAvailable([]));
    
    const g = ++gen.current;
    void refreshHistory(projectForRuns, name || "")
      .then((items) => {
        if (g !== gen.current) return;          
        if (items.length) void openRun(items[0].id, projectForRuns)
          .catch((e) => flash(`打开最近一次运行失败：${errText(e)}`));
      })
      .catch((e) => { if (g === gen.current) flash(`加载运行历史失败：${errText(e)}`); });

    if (name) {
      draft.current = null;
      void loadFromDisk().catch(() => flash("加载失败"));
    } else {
      const t: WorkflowDef = draft.current ?? DRAFT;
      draft.current = t;
      
      
      savedName.current = t.name;
      setWf(t);
      setInputVals({ input: "" });
      const { nodes, edges } = dslToCanvas(t);
      setRfNodes(nodes);
      setRfEdges(edges);
      idCounter.current = 1;
      
      
      lastSaved.current = saveKey(t, nodes, edges,
                                  t.parallel_mode === "agent" ? "agent" : "sequential");
      setSaveState("saved");
      loaded.current = true;
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
    
    
  }, [name, project, projectForRuns]);
}

