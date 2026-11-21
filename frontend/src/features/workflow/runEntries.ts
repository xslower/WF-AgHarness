
import type { WfRun } from "../../kernel/api";

export interface RunEntryDeps {
  
  wfName: string;
  
  projectForRuns: string;
  project: string;
  inputVals: Record<string, string>;
  parallelMode: "agent" | "sequential";
  selId: string | null;
  flash: (t: string) => void;
  
  save: () => Promise<boolean>;
}

export interface StartRunOpts {
  wfName: string;
  project: string;
  inputVals: Record<string, string>;
  parallelMode: "agent" | "sequential";
  flash: (t: string) => void;
}

export interface RunSingleOpts {
  wfName: string;
  selId: string;
  project: string;
  inputVals: Record<string, string>;
  flash: (t: string) => void;
}

export interface RunFromOpts extends RunSingleOpts {
  parallelMode: "agent" | "sequential";
}

export function makeRunEntries(deps: RunEntryDeps, hooks: {
  startRun: (o: StartRunOpts) => Promise<void>;
  runSingleNode: (o: RunSingleOpts) => Promise<void>;
  startRunFrom: (o: RunFromOpts) => Promise<void>;
}) {
  const { wfName, project, projectForRuns, inputVals, parallelMode,
    selId, flash, save } = deps;

  
  const saveThenRun = async (opts: {
    needSelection?: boolean;
    failHint: string;
    missingHint?: string;
  }): Promise<RunEntryDeps | null> => {
    if (!opts.needSelection) {
      if (!wfName) { flash(opts.missingHint ?? "先保存工作流再运行"); return null; }
    } else if (!wfName || !selId) {
      flash(opts.missingHint ?? "先选中节点");
      return null;
    }
    if (!(await save())) { flash(opts.failHint); return null; }
    return deps;
  };

  return {
    
    startRun: async () => {
      const d = await saveThenRun({ failHint: "保存失败，未启动运行" });
      if (!d) return;
      await hooks.startRun({ wfName, project: projectForRuns, inputVals,
        parallelMode, flash });
    },

    
    runSingleNode: async () => {
      const d = await saveThenRun({ needSelection: true,
        failHint: "保存失败，未启动试运行" });
      if (!d || !d.selId) return;
      await hooks.runSingleNode({ wfName, selId: d.selId, project, inputVals, flash });
    },

    
    startRunFrom: async () => {
      const d = await saveThenRun({ needSelection: true,
        failHint: "保存失败，未启动运行" });
      if (!d || !d.selId) return;
      await hooks.startRunFrom({ wfName, selId: d.selId, project, inputVals,
        parallelMode, flash });
    },
  };
}


export function isRunning(run: WfRun | null): boolean {
  return run?.status === "running";
}
