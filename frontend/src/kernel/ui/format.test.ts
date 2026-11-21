
import { describe, expect, it } from "vitest";
import {
  baseName, fmtBytes, fmtClock, fmtCost, fmtSize, fmtStamp, fmtTime,
  fmtTokens, nowHM, shortTime, tailLine,
} from "./format";

describe("数字与字节", () => {
  it("token 缩写：千用 k，百万用 M，两处消费者看到同一个数", () => {
    expect(fmtTokens(999)).toBe("999");
    expect(fmtTokens(1234)).toBe("1.2k");
    expect(fmtTokens(100000)).toBe("100.0k");
    expect(fmtTokens(2_500_000)).toBe("2.50M");
  });

  it("fmtBytes 带空格、fmtSize 紧凑，只差展示密度不差口径", () => {
    expect(fmtBytes(512)).toBe("512 B");
    expect(fmtBytes(1536)).toBe("1.5 KB");
    expect(fmtSize(512)).toBe("512B");
    expect(fmtSize(1536)).toBe("1.5K");
    expect(fmtSize(2 * 1024 * 1024)).toBe("2.0M");
    expect(fmtBytes(2 * 1024 * 1024)).toBe("2.0 MB");
  });

  it("小额费用保留有效位", () => {
    expect(fmtCost(0.000012)).toBe("0.00001");
    expect(fmtCost(1.23456)).toBe("1.235");
  });
});

describe("时间", () => {
  
  const noon = (() => { const d = new Date(); d.setHours(12, 34, 56, 0); return d; })();
  const todayTs = Math.floor(noon.getTime() / 1000);
  const oldTs = Math.floor(new Date(2026, 0, 2, 9, 5, 0).getTime() / 1000);

  it("shortTime 同一天只给时分，跨天补月日", () => {
    expect(shortTime(todayTs)).toBe("12:34");
    expect(shortTime(oldTs)).toBe("01-02 09:05");
  });

  it("fmtClock 带秒；fmtStamp 带年份且空值安全", () => {
    expect(fmtClock(todayTs)).toBe("12:34:56");
    expect(fmtStamp(oldTs)).toMatch(/^2026-01-02 09:05$/);
    expect(fmtStamp(null)).toBe("");
    expect(fmtStamp("not a number")).toBe("");
  });

  it("fmtTime 兼容秒与毫秒两种输入", () => {
    expect(fmtTime(todayTs)).toBe("12:34");
    expect(fmtTime(noon.getTime())).toBe("12:34");
    expect(fmtTime(undefined)).toBe("");
  });

  it("nowHM 是 HH:MM", () => {
    expect(nowHM()).toMatch(/^\d{2}:\d{2}$/);
  });
});

describe("路径与文本", () => {
  it("baseName 兼容 / 与 \\，尾斜杠按目录本身处理（三处消费者统一）", () => {
    expect(baseName("out/a/b.md")).toBe("b.md");
    expect(baseName("C:\\work\\out\\b.md")).toBe("b.md");
    expect(baseName("plain.md")).toBe("plain.md");
    expect(baseName("a/b/")).toBe("b");
    expect(baseName("")).toBe("");
  });

  it("tailLine 取最后一行非空内容", () => {
    expect(tailLine("第一行\n\n  \n最后一行")).toBe("最后一行");
    expect(tailLine("")).toBe("");
  });
});
