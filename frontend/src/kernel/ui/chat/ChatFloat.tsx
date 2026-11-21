
import { FloatPanel } from "../FloatPanel";
import { ApprovalCard } from "./ApprovalCard";
import PlanCard from "./PlanCard";
import type { ChatStream } from "./useChatStream";

export function ChatFloat({ chat, onEditPlan }: {
  chat: ChatStream;
  
  onEditPlan?: (planText: string) => void;
}) {
  const awaiting = chat.planState.status === "awaiting_approval";
  const approvals = chat.pendingApprovals;
  if (!awaiting && approvals.length === 0) return null;

  const title = awaiting
    ? "计划待确认"
    : approvals.length > 1
      ? `⚠ ${approvals.length} 项待审批`
      : "⚠ 操作待审批";

  return (
    <FloatPanel storeKey="chat" title={title} accent={awaiting ? "warn" : "info"}>
      {awaiting && (
        <PlanCard
          planState={chat.planState}
          onApprove={() => chat.sendPlanDecision("approve")}
          onModify={(fb) => {
            
            
            
            
            void chat.send(fb, { plan: true });
          }}

          onEditFull={(text) => onEditPlan?.(text)}
          onCancel={() => chat.sendPlanDecision("cancel")}
          busy={chat.busy}
        />
      )}
      {approvals.map((a) => (
        <ApprovalCard key={a.id} item={a} onDone={() => chat.removeApproval(a.id)} />
      ))}
    </FloatPanel>
  );
}
