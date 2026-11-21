
export function nextWorkflowName(existing: readonly string[]): string {
  const d = new Date();
  const base = `工作流-${d.getMonth() + 1}${d.getDate()}`;
  if (!existing.includes(base)) return base;
  let i = 1;
  let name = base;
  while (existing.includes(name)) name = `${base}-${++i}`;
  return name;
}
