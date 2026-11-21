
import { api } from "../../kernel/api";
import type { WfRun } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";

interface RedoDeps {
  run: WfRun | null;
  project: string;
  flash: (t: string) => void;
  
  follow: (runId: string) => Promise<void>;
  
  refresh: () => Promise<unknown>;
}


export async function redoFrom(d: RedoDeps, nodeId: string, note = ""): Promise<boolean> {
  if (!d.run) {
    d.flash("当前没有可重跑的运行；先从历史里打开一条");
    return false;
  }
  if (!nodeId) {
    d.flash("先选中要重跑的节点");
    return false;
  }
  d.flash(`↻ 从 ${nodeId} 重跑中…`);
  try {
    const { run_id } = await api.wfRunRedo(d.run.id, nodeId, note, d.project);
    await d.follow(run_id);
    await d.refresh();
    d.flash(`✓ 已从 ${nodeId} 重跑`);
    return true;
  } catch (e) {
    d.flash(`重跑失败：${errText(e)}`);
    return false;
  }
}
