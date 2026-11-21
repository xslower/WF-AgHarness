
export function pickSessionId(
  localSid: string | null,
  listIds: string[],
  boundId: string | null,
): string | null {
  if (localSid && listIds.includes(localSid)) return localSid;
  return boundId ?? null;
}
