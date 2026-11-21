
import { api } from "../../kernel/api";
import type { WfAvailable, WorkflowDef } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import { needsRunDialog, prefillInputs, renameWorkflow } from "./editorActions";

export interface WorkflowCommandDeps {
  project: string;
  wf: WorkflowDef | null;
  savedName: { current: string };
  lastSaved: { current: string };
  save: () => Promise<boolean>;
  setWf: (w: WorkflowDef) => void;
  setInputVals: (upd: (v: Record<string, string>) => Record<string, string>) => void;
  setRunAsk: (v: boolean) => void;
  setNameEdit: (v: string | null) => void;
  
  pendingName: string | null;
  startRun: () => void;
  flash: (text: string, ms?: number) => void;
  onChanged: () => void;
  onOpenWorkflow?: (project: string, name: string) => void;
  available: WfAvailable[];
  
  lastRev: { current: string };
  
  saveKeyOf: (w?: WorkflowDef) => string;
}

export interface WorkflowCommands {
  togglePublish: () => Promise<void>;
  doRun: () => void;
  confirmName: () => Promise<void>;
  openSubWorkflow: (sub: string) => void;
}

export function makeWorkflowCommands(d: WorkflowCommandDeps): WorkflowCommands {
  
  const togglePublish = async () => {
    const wf = d.wf;
    if (!wf) return;
    const status = String((wf as { status?: string }).status || "draft");
    const next: "published" | "draft" = status === "published" ? "draft" : "published";
    try {
      if (!(await d.save())) return;      
      const r = (await api.wfSetStatus(wf.name, next, "")) as
        { _revision?: string } | null;
      
      
      const rev = String(r?._revision || "");
      const nextWf = { ...wf, status: next, ...(rev ? { _revision: rev } : {}) } as WorkflowDef;
      d.setWf(nextWf);
      if (rev) {
        d.lastRev.current = rev;
        d.lastSaved.current = d.saveKeyOf(nextWf);
      }
      d.flash(next === "published" ? "✓ 已发布（全局主页可见）" : "✓ 已撤回发布");
      d.onChanged();
    } catch (e) {
      d.flash(`发布失败：${errText(e)}`);
    }
  };

  const doRun = () => {
    if (!d.wf) return;
    if (!needsRunDialog(d.wf)) { d.startRun(); return; }
    
    d.setInputVals((v) => prefillInputs(d.wf!, v));
    d.setRunAsk(true);
  };

  
  const confirmName = async () => {
    const wf = d.wf;
    if (!wf) return;
    const next = d.pendingName;
    d.setNameEdit(null);
    if (next === null) return;
    await renameWorkflow({
      next, current: wf, savedName: d.savedName.current, project: d.project, flash: d.flash,
      setWf: d.setWf,
      onRenamed: (newName, saved) => {
        d.savedName.current = newName;
        
        
        d.lastRev.current = String(saved._revision || "");
        d.lastSaved.current = d.saveKeyOf(saved);
      },
      onChanged: d.onChanged,
    });
  };

  
  const openSubWorkflow = (sub: string) => {
    if (!sub || sub === d.wf?.name) return;
    const hit = d.available.find((w) => w.name === sub);
    if (hit?.scope === "global" && d.project) {
      d.flash(`「${sub}」来自全局复用库；在这里保存会在当前项目建一份副本`);
    }
    if (d.onOpenWorkflow) d.onOpenWorkflow(d.project, sub);
    else d.flash("当前入口不支持跳转，请从侧栏打开这个工作流");
  };

  return { togglePublish, doRun, confirmName, openSubWorkflow };
}
