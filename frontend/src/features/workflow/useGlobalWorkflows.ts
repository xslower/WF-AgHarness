
import { useCallback, useState } from "react";

import { api } from "../../kernel/api";
import type { WorkflowSummary } from "../../kernel/api";
import { confirmDialog } from "../../kernel/ui/dialog";
import { errText } from "../../kernel/ui/errText";
import { nextWorkflowName } from "./workflowName";


const NEW_GLOBAL_FLOW_NODES = [{ id: "s1", type: "llm", prompt: "处理：${inputs.input}" }];

export interface GlobalWorkflowsController {
  list: WorkflowSummary[];
  error: string;
  creating: boolean;
  openName: string | null;
  setOpenName: (name: string | null) => void;
  refresh: () => Promise<void>;
  create: () => Promise<void>;
  remove: (name: string) => Promise<void>;
  togglePublish: (w: WorkflowSummary) => Promise<void>;
}

export function useGlobalWorkflows(): GlobalWorkflowsController {
  const [list, setList] = useState<WorkflowSummary[]>([]);
  const [openName, setOpenName] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setList(await api.wfList(""));
      setError("");
    } catch (e) {
      setError(`工作流列表加载失败: ${errText(e)}`);
    }
  }, []);

  
  const create = async () => {
    if (creating) return;
    const name = nextWorkflowName(list.map((w) => w.name));
    setCreating(true);
    try {
      await api.wfSave({
        name,
        desc: "",
        inputs: [{ name: "input", desc: "输入文本", type: "string" }],
        nodes: NEW_GLOBAL_FLOW_NODES,
        edges: [],
      }, "");
      await refresh();
      setOpenName(name);
      setError("");
    } catch (e) {
      setError(`新建失败: ${errText(e)}`);
    } finally {
      setCreating(false);
    }
  };

  const remove = async (name: string) => {
    if (!(await confirmDialog({
      title: "删除全局工作流",
      danger: true,
      okText: "删除",
      message: `确认删除全局工作流「${name}」？引用它的子工作流节点会失效。`,
    }))) return;
    try {
      await api.wfDelete(name, "");
      await refresh();
    } catch (e) {
      setError(`删除失败: ${errText(e)}`);
    }
  };

  const togglePublish = async (w: WorkflowSummary) => {
    const next = (w.status || "draft") === "published" ? "draft" : "published";
    try {
      await api.wfSetStatus(w.name, next, "");
      await refresh();
    } catch (e) {
      setError(`发布状态更新失败: ${errText(e)}`);
    }
  };

  return {
    list, error, creating, openName, setOpenName,
    refresh, create, remove, togglePublish,
  };
}
