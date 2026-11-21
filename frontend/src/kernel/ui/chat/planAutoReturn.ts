
import { readField, writeField } from "../../chat/chatSessionStore";


export const PLAN_RETURN_AFTER = 5;


const WHOLE_PLAN_REQUEST = new RegExp(
  "^(计划|方案|规划|出个?方案|给个?计划|做个?计划|写个?方案|"
  + "切回计划|开启计划|回到计划|plan mode|make a plan|give me a plan)"
  + "[\\s?!。,.，]*$", "i");


const FOLLOWING_PLAN = /(按|照|依|根据|顺着)[^，。；!?\n]{0,4}(计划|方案|规划)/;


const PLAN_REQUEST_PATTERNS: RegExp[] = [
  
  /(出|给|来|做|写|列|拟|定|编|准备|整理|重新|另外|换个|切回|开启|回到|启用|恢复|重写|重出|要不要|能不能|有没有|想看|先)[^，。；!?\n]{0,8}(计划|方案|规划)/i,
  
  /(计划|方案|规划)[^，。；!?\n]{0,4}(给我|发我|列出来|看看|呢|吧|模式)/i,
  
  /\bplan mode\b|\b(make|give me|write|draft|show me)\b[^.!?\n]{0,20}\bplan\b/i,
];


export function wantsPlan(text: string): boolean {
  const t = (text || "").trim();
  if (!t) return false;
  if (WHOLE_PLAN_REQUEST.test(t)) return true;
  if (FOLLOWING_PLAN.test(t)) return false;
  return PLAN_REQUEST_PATTERNS.some((re) => re.test(t));
}

interface AutoState { armed: boolean; count: number }

const IDLE: AutoState = { armed: false, count: 0 };

function read(sid: string | null): AutoState {
  if (!sid) return IDLE;
  const v = readField(sid, "planAuto", IDLE as unknown as Record<string, unknown>);
  return { armed: v.armed === true, count: Number(v.count) || 0 };
}

function write(sid: string | null, s: AutoState): void {
  if (!sid) return;
  writeField(sid, "planAuto", s as unknown as Record<string, unknown>);
}


export function armPlanAutoReturn(sid: string | null): void {
  write(sid, { armed: true, count: 0 });
}


export function resetPlanAutoReturn(sid: string | null): void {
  write(sid, IDLE);
}


const APPROVE_RE = new RegExp(
  "^(确认|同意|执行|开始|没问题|可以|好的|ok|yes|go|行|好|干|搞|来吧)"
  + "|(确认|同意).*(执行|开始|操作)"
  + "|(开始|直接|马上).*(执行|操作|搞)"
  + "|^没问题.*(执行|开始|做)"
  + "|^好的.*(没问题|可以|行|确认|执行|开始)"
  + "|^按.*(计划|plan).*(执行|来|做)", "i");

export function isApproval(text: string): boolean {
  return APPROVE_RE.test((text || "").trim());
}

export type PlanVerdict = "idle" | "stay" | "keyword" | "reached";


export function noteUserMessage(sid: string | null, text: string): PlanVerdict {
  const st = read(sid);
  if (!st.armed) return "idle";
  if (wantsPlan(text)) {
    resetPlanAutoReturn(sid);
    return "keyword";
  }
  const count = st.count + 1;
  if (count >= PLAN_RETURN_AFTER) {
    resetPlanAutoReturn(sid);
    return "reached";
  }
  write(sid, { armed: true, count });
  return "stay";
}
