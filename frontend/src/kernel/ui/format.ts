

function pad2(x: number): string {
  return String(x).padStart(2, "0");
}




export function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}


export function fmtCost(v: number): string {
  return v < 0.01 ? v.toFixed(5).replace(/0+$/, "").replace(/\.$/, "") : v.toFixed(3);
}


export function fmtCostText(v: number): string {
  return `¥${fmtCost(v)}`;
}


export const TOKENS_PER_K = 1024;
export function tokensToK(n: number): number { return Math.round(n / TOKENS_PER_K); }
export function kToTokens(k: number): number { return Math.round(k) * TOKENS_PER_K; }


export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1_048_576) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1_048_576).toFixed(1)} MB`;
}


export function fmtSize(n: number): string {
  if (n < 1024) return `${n}B`;
  if (n < 1_048_576) return `${(n / 1024).toFixed(1)}K`;
  return `${(n / 1_048_576).toFixed(1)}M`;
}




function isSameDay(d: Date, ref: Date): boolean {
  return d.getFullYear() === ref.getFullYear()
    && d.getMonth() === ref.getMonth()
    && d.getDate() === ref.getDate();
}


export function fmtClock(ts: number): string {
  const d = new Date(ts * 1000);
  const hms = `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
  return isSameDay(d, new Date())
    ? hms
    : `${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${hms.slice(0, 5)}`;
}


export function fmtStamp(ts?: number | string | null): string {
  const n = typeof ts === "string" ? Number(ts) : ts;
  if (!n || !Number.isFinite(n)) return "";
  const d = new Date(n * 1000);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} `
    + `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}


export function shortTime(ts: number): string {
  const d = new Date(ts * 1000);
  const hm = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  return isSameDay(d, new Date())
    ? hm
    : `${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${hm}`;
}


export function fmtTime(ts?: number): string {
  if (!ts) return "";
  const d = new Date(ts > 1e12 ? ts : ts * 1000);
  if (Number.isNaN(d.getTime())) return "";
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}


export function nowHM(): string {
  const d = new Date();
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}




export function baseName(p: string): string {
  const s = String(p || "").replace(/[\\/]+$/, "");
  const i = Math.max(s.lastIndexOf("/"), s.lastIndexOf("\\"));
  return i >= 0 ? s.slice(i + 1) : s;
}


export function tailLine(text: string, max = 110): string {
  const lines = text.split("\n").filter((x) => x.trim());
  const last = lines[lines.length - 1] || "";
  return last.length > max ? last.slice(-max) : last;
}

