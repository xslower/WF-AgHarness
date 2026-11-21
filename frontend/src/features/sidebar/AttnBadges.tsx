
import type { Attn } from "../../kernel/attention/attn";
import { hasAny, waitingCount } from "../../kernel/attention/attn";


export function attnTitle(a: Attn): string {
  const parts: string[] = [];
  if (a.approvals) parts.push(`${a.approvals} 个工具审批待处理（允许/拒绝）`);
  if (a.human) parts.push(`${a.human} 个工作流人工闸门等你拍板`);
  if (a.plan) parts.push("计划已出，等你确认执行");
  if (a.running) parts.push("正在运行");
  if (a.queued) parts.push(`排队 ${a.queued} 条消息`);
  if (a.fresh) parts.push(`${a.fresh} 条有新结果未查看`);
  return parts.join("；");
}

export function AttnBadges({ attn }: { attn: Attn }) {
  if (!hasAny(attn)) return null;
  const waiting = waitingCount(attn);
  return (
    <>
      {waiting > 0 && (
        
        
        <span className="sess-badge wait" title={attnTitle(attn)}>
          待{waiting > 1 ? waiting : ""}
        </span>
      )}
      {attn.running > 0 && (
        <span className="sess-badge run" title={attnTitle(attn)}>●</span>
      )}
      {attn.queued > 0 && (
        <span className="sess-badge queue" title={`排队 ${attn.queued} 条`}>{attn.queued}</span>
      )}
      {waiting === 0 && attn.fresh > 0 && (
        <span className="sess-badge unread" title={attnTitle(attn)}>●</span>
      )}
    </>
  );
}
