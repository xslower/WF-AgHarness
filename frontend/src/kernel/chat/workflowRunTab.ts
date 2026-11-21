
export interface WorkflowRunOpenRequest {
  
  runId: string;
  
  workflow?: string;
  
  project?: string;
}

let opener: ((req: WorkflowRunOpenRequest) => void) | null = null;

export function bindWorkflowRunOpener(
  fn: ((req: WorkflowRunOpenRequest) => void) | null,
): void {
  opener = fn;
}

export function openWorkflowRunTab(req: WorkflowRunOpenRequest): void {
  opener?.(req);
}


const RUN_ID_RE = /\[run_id:([A-Za-z0-9_-]+)\]/;

export function runIdFromResult(result: string | undefined): string {
  const m = RUN_ID_RE.exec(String(result || ""));
  return m ? m[1] : "";
}
