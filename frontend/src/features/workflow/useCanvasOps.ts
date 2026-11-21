
import { useCallback } from "react";
import type { Edge, Node } from "@xyflow/react";
import { api } from "../../kernel/api";
import type { WfAvailable } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import { buildSubflow, uniqueName } from "./extract";
import { buildNodeDsl, canAddNode, connectEdges, nodeId, placeNewNode, removeNode } from "./graphOps";
import type { PaletteItem } from "./Palette";
import { type FlowNodeData } from "./dsl";
import { confirmDialog } from "../../kernel/ui/dialog";

export interface CanvasOpsDeps {
  rfNodes: Node[];
  rfEdges: Edge[];
  setRfNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  setRfEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
  selId: string | null;
  setSelId: (id: string | null) => void;
  idCounter: { current: number };
  
  items: PaletteItem[];
  
  available: WfAvailable[];
  setAvailable: (list: WfAvailable[]) => void;
  project: string;
  
  wfName: string;
  flash: (text: string) => void;
  onChanged: () => void;
  
  onCodeNodeCreated: () => void;
}

export function useCanvasOps(deps: CanvasOpsDeps) {
  const {
    rfNodes, rfEdges, setRfNodes, setRfEdges, selId, setSelId, idCounter,
    items, available, setAvailable, project, wfName, flash, onChanged,
    onCodeNodeCreated,
  } = deps;

  const addNode = useCallback((item: PaletteItem, extra?: Record<string, unknown>) => {
    if (!canAddNode(false, item.type)) return;
    idCounter.current += 1;
    const id = nodeId(item.type, idCounter.current);
    const dsl = buildNodeDsl(item, id, extra);
    setRfNodes((ns) => [...ns, {
      id, type: "dsl",
      position: placeNewNode(ns.length),
      data: { dsl } as FlowNodeData,
    }]);
    setSelId(id);
  }, [setRfNodes, setSelId, idCounter]);

  const addLlmNode = () => {
    const item = items.find((i) => i.type === "llm");
    if (item) addNode(item);
  };

  const onConnect = useCallback((c: { source?: string | null; target?: string | null;
                                       sourceHandle?: string | null;
                                       targetHandle?: string | null }) => {
    if (!c.source || !c.target) return;
    const src = c.source, dst = c.target;
    setRfEdges((es) => connectEdges(es, {
      source: src, target: dst,
      sourceHandle: c.sourceHandle ?? null, targetHandle: c.targetHandle ?? null,
    }));
  }, [setRfEdges]);

  const patchDsl = (key: string, value: string) => {
    if (!selId) return;
    setRfNodes((ns) => ns.map((n) => n.id === selId
      ? { ...n, data: { ...(n.data as FlowNodeData), dsl: { ...((n.data as FlowNodeData).dsl), [key]: value } } }
      : n));
  };

  const deleteSelected = () => {
    if (!selId) return;
    setRfNodes((ns) => ns.filter((n) => n.id !== selId));
    setRfEdges((es) => removeNode(es, selId));
    setSelId(null);
  };

  const deleteNode = (id: string) => {
    setRfNodes((ns) => ns.filter((n) => n.id !== id));
    setRfEdges((es) => removeNode(es, id));
    if (selId === id) setSelId(null);
  };

  const copyNode = (id: string) => {
    const n = rfNodes.find((x) => x.id === id);
    if (!n) return;
    const dsl = { ...((n.data as FlowNodeData).dsl as Record<string, unknown>) };
    idCounter.current += 1;
    const nid = nodeId(String(dsl.type), idCounter.current);
    dsl.id = nid;
    setRfNodes((ns) => [...ns, {
      id: nid, type: "dsl",
      position: { x: n.position.x + 60, y: n.position.y + 60 },
      data: { dsl } as FlowNodeData,
    }]);
    setSelId(nid);
  };

  
  const doExtract = async () => {
    if (!selId || !wfName) return flash("先选中要抽的节点并保存工作流");
    const base = `${wfName}-${selId}`;
    const subName = uniqueName(base, available.map((w) => w.name));
    idCounter.current += 1;
    const newNodeId = nodeId("workflow", idCounter.current);
    const res = buildSubflow(rfNodes, rfEdges, selId, subName, newNodeId);
    if (!res) return flash("这一段抽不出来（没有可接的节点）");
    if (res.moved.length < 2) {
      const ok = await confirmDialog({
        title: "只抽到一个节点",
        message: `从「${selId}」开始只有 ${res.moved.length} 个节点能被抽出来（遇到分叉/汇合就停了）。`
          + "只有一个节点的子工作流通常没什么意义，仍要继续吗？",
        okText: "继续抽取",
      });
      if (!ok) return;
    }
    
    
    const toGlobal = await confirmDialog({
      title: "存到哪里",
      message: `子工作流「${subName}」放在哪儿？\n\n`
        + "全局复用库：所有项目都能用 workflow 节点引用（推荐给通用片段）；\n"
        + "本项目：只有当前项目能看到。",
      okText: "存到全局复用库",
      cancelText: "只存本项目",
    });
    try {
      await api.wfSave(res.sub, toGlobal ? "" : project);
      
      
      await api.wfAvailable(project).then(setAvailable)
        .catch((e) => flash(`子工作流列表刷新失败：${errText(e)}`));
      setRfNodes(res.nodes);
      setRfEdges(res.edges);
      setSelId(res.newNodeId);
      flash(`✓ 已抽成子工作流「${subName}」（${res.moved.length} 个节点，`
        + `${toGlobal ? "全局复用库" : "本项目"}）`);
      onChanged();
    } catch (e) {
      flash(`抽取失败: ${e}`);
    }
  };

  
  const createCodeNode = (template: string) => {
    const it = items.find((i) => i.type === "code");
    if (it) addNode(it, { code: template, lang: "python" });
    onCodeNodeCreated();
  };

  return {
    addNode, addLlmNode, createCodeNode, onConnect, patchDsl,
    deleteSelected, deleteNode, copyNode, doExtract,
  };
}
