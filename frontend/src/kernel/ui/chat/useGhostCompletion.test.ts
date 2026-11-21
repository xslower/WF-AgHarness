

import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { api } from "../../api";
import { useGhostCompletion } from "./useGhostCompletion";

beforeEach(() => { vi.restoreAllMocks(); });

describe("输入补全禁用档", () => {
  it("禁用时不发任何请求、浮窗为空", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(api, "suggestInput").mockResolvedValue({ completion: "的任务" });
    const { result } = renderHook(() => useGhostCompletion({ sessionId: "s1", enabled: false }));

    act(() => result.current.request("帮我写"));
    await act(async () => { vi.advanceTimersByTime(600); await Promise.resolve(); });

    expect(spy).not.toHaveBeenCalled();
    expect(result.current.ghost).toBe("");
    vi.useRealTimers();
  });

  it("启用时停顿后请求补全", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(api, "suggestInput").mockResolvedValue({ completion: "的任务" });
    const { result } = renderHook(() => useGhostCompletion({ sessionId: "s1", enabled: true }));

    act(() => result.current.request("帮我写"));
    await act(async () => { vi.advanceTimersByTime(600); await Promise.resolve(); });

    expect(spy).toHaveBeenCalledWith("帮我写", "s1");
    expect(result.current.ghost).toBe("的任务");
    vi.useRealTimers();
  });

  it("请求在途时切成禁用：取消定时器、不再发请求", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(api, "suggestInput").mockResolvedValue({ completion: "x" });
    const { result, rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) => useGhostCompletion({ sessionId: "s1", enabled }),
      { initialProps: { enabled: true } },
    );

    act(() => result.current.request("帮我写"));   
    act(() => { rerender({ enabled: false }); });
    await act(async () => { vi.advanceTimersByTime(600); await Promise.resolve(); });

    expect(spy).not.toHaveBeenCalled();
    expect(result.current.ghost).toBe("");
    vi.useRealTimers();
  });

  it("切成禁用时清掉已显示的补全浮窗", async () => {
    vi.useFakeTimers();
    vi.spyOn(api, "suggestInput").mockResolvedValue({ completion: "的任务" });
    const { result, rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) => useGhostCompletion({ sessionId: "s1", enabled }),
      { initialProps: { enabled: true } },
    );

    act(() => result.current.request("帮我写"));
    await act(async () => { vi.advanceTimersByTime(600); await Promise.resolve(); });
    expect(result.current.ghost).toBe("的任务");

    act(() => { rerender({ enabled: false }); });
    expect(result.current.ghost).toBe("");
    vi.useRealTimers();
  });

  it("少于 3 字仍不请求（避免每打一个字就打模型）", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(api, "suggestInput").mockResolvedValue({ completion: "x" });
    const { result } = renderHook(() => useGhostCompletion({ sessionId: null, enabled: true }));

    act(() => result.current.request("你"));
    await act(async () => { vi.advanceTimersByTime(600); await Promise.resolve(); });

    expect(spy).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
