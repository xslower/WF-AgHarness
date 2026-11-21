
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createCoalescer, isProjectEvent, normPath } from "./eventRefresh";

describe("normPath", () => {
  it("反斜杠转正斜杠、去尾分隔符、忽略大小写", () => {
    expect(normPath("C:\\proj\\sub\\")).toBe("c:/proj/sub");
    expect(normPath("/home/u/share/")).toBe("/home/u/share");
    expect(normPath("/home/u/share")).toBe("/home/u/share");
  });

  it("非字符串安全（null/undefined/数字）", () => {
    expect(normPath(null)).toBe("");
    expect(normPath(undefined)).toBe("");
    expect(normPath(123)).toBe("123");
  });

  it("只去尾部斜杠，不动中间的", () => {
    expect(normPath("/a/b//")).toBe("/a/b");
    expect(normPath("/")).toBe("");
  });
});

describe("isProjectEvent", () => {
  it("project 命中", () => {
    expect(isProjectEvent({ project: "/p" }, "/p")).toBe(true);
  });

  it("project_real 不再参与判断（后端只发归一后的 project）", () => {
    expect(isProjectEvent({ project: "/home/u/share",
                            project_real: "/media/u/disk/share" },
                          "/media/u/disk/share")).toBe(false);
  });

  it("大小写与斜杠差异不影响判断", () => {
    expect(isProjectEvent({ project: "C:\\Proj\\" }, "c:/proj")).toBe(true);
  });

  it("别的项目不刷新", () => {
    expect(isProjectEvent({ project: "/other" }, "/p")).toBe(false);
    expect(isProjectEvent({}, "/p")).toBe(false);
  });

  it("当前项目为空时永不算命中（否则所有事件都刷空面板）", () => {
    expect(isProjectEvent({ project: "" }, "")).toBe(false);
    expect(isProjectEvent({ project: "/p" }, "")).toBe(false);
  });

  it("payload 为空安全", () => {
    expect(isProjectEvent(undefined, "/p")).toBe(false);
    expect(isProjectEvent(null, "/p")).toBe(false);
  });
});

describe("createCoalescer", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("delay 内多次触发只执行一次", () => {
    const run = vi.fn();
    const c = createCoalescer(300, run);
    c.fire();
    c.fire();
    c.fire();
    expect(run).not.toHaveBeenCalled();
    vi.advanceTimersByTime(299);
    expect(run).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("间隔超过 delay 的分批触发各自执行", () => {
    const run = vi.fn();
    const c = createCoalescer(300, run);
    c.fire();
    vi.advanceTimersByTime(300);
    c.fire();
    vi.advanceTimersByTime(300);
    expect(run).toHaveBeenCalledTimes(2);
  });

  it("cancel 取消未执行的回调", () => {
    const run = vi.fn();
    const c = createCoalescer(300, run);
    c.fire();
    c.cancel();
    vi.advanceTimersByTime(1000);
    expect(run).not.toHaveBeenCalled();
  });

  it("执行完之后还能再次 fire", () => {
    const run = vi.fn();
    const c = createCoalescer(300, run);
    c.fire();
    vi.advanceTimersByTime(300);
    c.fire();
    vi.advanceTimersByTime(300);
    expect(run).toHaveBeenCalledTimes(2);
  });

  it("cancel 之后 fire 仍然有效（卸载前误 cancel 不影响后续）", () => {
    const run = vi.fn();
    const c = createCoalescer(300, run);
    c.cancel();
    c.fire();
    vi.advanceTimersByTime(300);
    expect(run).toHaveBeenCalledTimes(1);
  });
});
