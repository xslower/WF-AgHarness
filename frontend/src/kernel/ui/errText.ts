
export function errText(e: unknown): string {
  if (e instanceof Error) return e.message || e.name;
  const anyE = e as { message?: unknown } | null;
  if (anyE && typeof anyE.message === "string") return anyE.message;
  return String(e);
}
