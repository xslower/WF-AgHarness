
import { openWorkflowRunTab } from "../../chat/workflowRunTab";

export function OpenRunButton({ runId, workflow }: {
  runId: string;
  
  workflow?: string;
}) {
  return (
    <button className="link tool-open" title="在多功能栏查看这次运行的过程"
      onClick={(ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        openWorkflowRunTab({ runId, workflow });
      }}>查看过程</button>
  );
}
