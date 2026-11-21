
import { useCallback, useEffect, useRef, useState } from "react";
import type { Edge, Node } from "@xyflow/react";
import { api } from "../../kernel/api";
import type { WorkflowDef } from "../../kernel/api";
import { canvasToDsl } from "./dsl";

export type SaveState = "saved" | "dirty" | "saving" | "error";

export function useAutoSave(opts: {
  project: string;
  onChanged: () => void;
}) {
  const { project, onChanged } = opts;
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [saveErr, setSaveErr] = useState("");
  
  const savedNameRef = useRef("");
  const lastSavedRef = useRef("");
  
  const lastRevRef = useRef("");
  const loadedRef = useRef(false);

  const saveKey = useCallback((w: WorkflowDef, ns: Node[], es: Edge[], pm: "agent" | "sequential") =>
    JSON.stringify({ wf: canvasToDsl(w, ns, es), parallelMode: pm }), []);

  
  const doSave = useCallback(async (
    wf: WorkflowDef | null,
    rfNodes: Node[],
    rfEdges: Edge[],
    parallelMode: "agent" | "sequential",
  ): Promise<WorkflowDef | null> => {
    if (!wf) return null;
    if (!wf.name) { setSaveState("dirty"); setSaveErr("请先填写工作流名称"); return null; }
    setSaveState("saving");
    try {
      let toSave = canvasToDsl(wf, rfNodes, rfEdges);
      toSave.parallel_mode = parallelMode;
      
      toSave = {
        ...toSave,
        nodes: toSave.nodes.map((n) => {
          const rec = n as unknown as Record<string, unknown>;
          if (rec.type === "mcp" && rec.argsJson) {
            try { rec.args = JSON.parse(String(rec.argsJson)); } catch { rec.args = {}; }
            delete rec.argsJson;
          }
          return n;
        }),
      };
      const saved = await api.wfSave(toSave, project) as WorkflowDef;
      
      const oldName = savedNameRef.current;
      if (oldName && toSave.name !== oldName) {
        await api.wfDelete(oldName, project).catch(() => {});
      }
      savedNameRef.current = toSave.name;
      const savedWf = { ...toSave, ...(saved as WorkflowDef), name: toSave.name };
      lastSavedRef.current = saveKey(savedWf, rfNodes, rfEdges, parallelMode);
      lastRevRef.current = String((savedWf as { _revision?: string })._revision || "");
      setSaveState("saved");
      setSaveErr("");
      onChanged();
      return savedWf;
    } catch (e) {
      setSaveState("error");
      setSaveErr(String(e));
      return null;
    }
  }, [project, onChanged, saveKey]);

  return {
    saveState, setSaveState, saveErr, setSaveErr,
    savedNameRef, lastSavedRef, loadedRef, saveKey, doSave, lastRevRef,
  };
}
