
import { WorkflowRunTab } from "./WorkflowRunTab";

export function renderWorkflowRunTab(t: {
  runId: string; workflow: string; project: string;
}) {
  return <WorkflowRunTab runId={t.runId} workflow={t.workflow} project={t.project} />;
}
