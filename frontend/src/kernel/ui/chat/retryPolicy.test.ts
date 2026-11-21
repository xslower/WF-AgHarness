
import { describe, expect, it } from "vitest";
import { RETRY_BASE_MS, RETRY_MAX_MS, retryDelay } from "./retryPolicy";

describe("retryDelay", () => {
  it("指数退避：1s、2s、4s、8s", () => {
    expect(retryDelay(1)).toBe(1000);
    expect(retryDelay(2)).toBe(2000);
    expect(retryDelay(3)).toBe(4000);
    expect(retryDelay(4)).toBe(8000);
  });

  it("封顶 10s（8s 之后不再翻倍）", () => {
    expect(retryDelay(5)).toBe(RETRY_MAX_MS);
    expect(retryDelay(6)).toBe(RETRY_MAX_MS);
    for (const n of [10, 50, 999]) expect(retryDelay(n)).toBe(RETRY_MAX_MS);
  });

  it("常量就是契约本身（别被悄悄改成 5s 固定或其他值）", () => {
    expect(RETRY_BASE_MS).toBe(1000);
    expect(RETRY_MAX_MS).toBe(10_000);
  });

  it("异常入参不返回 0/Infinity（0 会变成重连风暴，Infinity 会永不重连）", () => {
    for (const n of [0, -5, 1e9]) {
      const d = retryDelay(n);
      expect(d).toBeGreaterThan(0);
      expect(Number.isFinite(d)).toBe(true);
      expect(d).toBeLessThanOrEqual(RETRY_MAX_MS);
    }
  });
});
