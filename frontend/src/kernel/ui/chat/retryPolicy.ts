


export const RETRY_BASE_MS = 1_000;

export const RETRY_MAX_MS = 10_000;


export function retryDelay(n: number): number {
  const k = Math.max(0, Math.floor(n) - 1);
  
  return Math.min(RETRY_MAX_MS, RETRY_BASE_MS * 2 ** Math.min(k, 16));
}
