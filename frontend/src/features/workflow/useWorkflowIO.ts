
import { useEffect, useRef, useState } from "react";
import type { Edge, Node } from "@xyflow/react";
import { api } from "../../kernel/api";
import type { WorkflowDef } from "../../kernel/api";
import { canvasToDsl, dslToCanvas } from "./dsl";

export interface WorkflowIODeps {
  wf: WorkflowDef | null;
  setWf: (w: WorkflowDef) => void;
  rfNodes: Node[];
  rfEdges: Edge[];
  setRfNodes: (nodes: Node[]) => void;
  setRfEdges: (edges: Edge[]) => void;
  idCounter: { current: number };
  project: string;
  flash: (text: string) => void;
  onChanged: () => void;
  setInputVals: (vals: Record<string, string>) => void;
}

export function useWorkflowIO(deps: WorkflowIODeps) {
  const {
    wf, setWf, rfNodes, rfEdges, setRfNodes, setRfEdges,
    idCounter, project, flash, onChanged, setInputVals,
  } = deps;

  const [jsonText, setJsonText] = useState("");
  
  const jsonDirty = useRef(false);
  const importRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!wf || jsonDirty.current) return;
    setJsonText(JSON.stringify(canvasToDsl(wf, rfNodes, rfEdges), null, 2));
  }, [wf, rfNodes, rfEdges]);

  
  const loadDsl = (parsed: WorkflowDef) => {
    setWf(parsed);
    const { nodes, edges } = dslToCanvas(parsed);
    setRfNodes(nodes);
    setRfEdges(edges);
    idCounter.current = parsed.nodes.length;
    jsonDirty.current = false;
  };

  const applyJson = () => {
    try {
      const parsed = JSON.parse(jsonText) as WorkflowDef;
      loadDsl(parsed);
      flash("✓ 已应用到画布");
    } catch (e) {
      flash(`JSON 无效: ${e}`);
    }
  };

  
  const resetJson = () => {
    if (!wf) return;
    jsonDirty.current = false;
    setJsonText(JSON.stringify(canvasToDsl(wf, rfNodes, rfEdges), null, 2));
  };

  const onImportFile = async (files: FileList | null) => {
    const f = files?.[0];
    if (!f) return;
    try {
      const parsed = JSON.parse(await f.text()) as WorkflowDef;
      await api.wfImport(parsed, project);
      loadDsl(parsed);
      setInputVals(Object.fromEntries((parsed.inputs ?? []).map((i) => [i.name, ""])));
      flash(`✓ 已导入「${parsed.name}」（模型已自动适配）`);
      onChanged();
    } catch (e) {
      flash(`导入失败: ${e}`);
    }
  };

  const doExport = async () => {
    if (!wf?.name) return flash("先保存工作流再导出");
    try {
      const data = await api.wfExport(wf.name, project);
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${wf.name}.workflow.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      flash(`导出失败: ${e}`);
    }
  };

  return {
    jsonText, setJsonText, jsonDirty, applyJson, resetJson,
    importRef, onImportFile, doExport,
  };
}
