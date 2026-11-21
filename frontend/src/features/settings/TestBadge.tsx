
import type { TestResult } from "../../kernel/api";

export function TestBadge({ spec, tests }: {
  spec: string;
  tests: Record<string, TestResult | "pending">;
}) {
  const t = tests[spec];
  if (t === "pending") return <span className="dim">测试中…</span>;
  if (!t) return null;
  if (t.skipped) {
    return <span className="dim" title={t.error}>— 不适用</span>;
  }
  return t.ok
    ? <span className="ok-badge" title={t.sample}>✓ {t.first_token_ms ?? t.ms}ms</span>
    : <span className="err-badge" title={t.error}>✗ 失败</span>;
}
