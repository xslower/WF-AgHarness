
import { api } from "../../kernel/api";
import type { WorkflowDef } from "../../kernel/api";
import { confirmDialog } from "../../kernel/ui/dialog";
import { scopedStore } from "../../kernel/ui/scopedStore";

export interface DeleteDeps {
  name: string;
  project: string;
  flash: (t: string) => void;
  
  stopAutosave: () => void;
  onChanged: () => void;
  onBack: () => void;
}


export async function deleteWorkflow(d: DeleteDeps): Promise<void> {
  if (!d.name) return;
  const ok = await confirmDialog({
    title: "删除工作流",
    danger: true,
    okText: "删除",
    message: `确定删除工作流「${d.name}」？此操作不可恢复。`,
  });
  if (!ok) return;
  try {
    await api.wfDelete(d.name, d.project);
    
    scopedStore.clearScope(`wf:${d.project || "global"}/${d.name}`);
    
    d.stopAutosave();
    d.flash("✓ 已删除");
    d.onChanged();
    d.onBack();
  } catch (e) {
    d.flash(`删除失败: ${e}`);
  }
}

export interface RenameDeps {
  
  next: string;
  current: WorkflowDef;
  
  savedName: string;
  project: string;
  flash: (t: string) => void;
  setWf: (wf: WorkflowDef) => void;
  onRenamed: (next: string, saved: WorkflowDef) => void;
  onChanged: () => void;
}


export async function renameWorkflow(d: RenameDeps): Promise<string> {
  const n = d.next.trim();
  if (!n || n === d.current.name) return "";
  if (!d.savedName) {
    d.setWf({ ...d.current, name: n });
    return n;
  }
  try {
    const saved = await api.wfRename(d.savedName, n, d.project) as WorkflowDef;
    const merged = { ...d.current, ...(saved as object), name: n };
    d.setWf(merged);
    d.onRenamed(n, merged);
    d.onChanged();
    d.flash("✓ 已重命名");
    return n;
  } catch (e) {
    d.flash(`重命名失败: ${e}`);
    return "";
  }
}


export function prefillInputs(wf: WorkflowDef | null,
                              vals: Record<string, string>): Record<string, string> {
  const next = { ...vals };
  for (const inp of wf?.inputs ?? []) {
    if ((next[inp.name] ?? "") === "" && inp.default) next[inp.name] = inp.default;
  }
  return next;
}


export function needsRunDialog(wf: WorkflowDef | null): boolean {
  return (wf?.inputs ?? []).length > 0;
}
