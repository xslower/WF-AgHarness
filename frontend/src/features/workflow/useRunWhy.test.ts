

import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { api } from "../../kernel/api";
import type { WfWhy } from "../../kernel/api";
import { useRunWhy } from "./useRunWhy";

const overview = (): WfWhy => ({
  query: "overview", workflow: "demo", status: "done",
  nodes: [{ node: "s1", status: "done", chars: 3, empty: false,
            reads: [], writes: ["s1"], ms: 5 }],
});

beforeEach(() => { vi.restoreAllMocks(); });

describe("useRunWhy", () => {
  it("问法互斥：只传对应那一个参数，其余留空", async () => {
    const spy = vi.spyOn(api, "wfRunWhy").mockResolvedValue(overview());
    const { result } = renderHook(() => useRunWhy("r1", "/p"));

    await act(async () => { await result.current.ask({ mode: "grep", value: "OUT" }); });
    expect(spy).toHaveBeenCalledWith("r1",
      { project: "/p", node: "", key: "", grep: "OUT" });

    await act(async () => { await result.current.ask({ mode: "key", value: "s1" }); });
    expect(spy).toHaveBeenLastCalledWith("r1",
      { project: "/p", node: "", key: "s1", grep: "" });

    await act(async () => { await result.current.ask({ mode: "overview", value: "" }); });
    expect(spy).toHaveBeenLastCalledWith("r1",
      { project: "/p", node: "", key: "", grep: "" });
  });

  it("切问法：先发的旧响应不得覆盖后发的结果", async () => {
    
    let release: ((v: WfWhy) => void) | null = null;
    vi.spyOn(api, "wfRunWhy")
      .mockImplementationOnce(() => new Promise<WfWhy>((res) => { release = res; }))
      .mockResolvedValueOnce({ query: "grep", grep: "X", hits: [] });

    const { result } = renderHook(() => useRunWhy("r1", "/p"));
    let first: Promise<void>;
    act(() => { first = result.current.ask({ mode: "node", value: "s2" }); });
    await act(async () => { await result.current.ask({ mode: "grep", value: "X" }); });
    expect(result.current.data?.query).toBe("grep");

    
    await act(async () => { release?.({ query: "node", node: "s2", reads: [],
      writes: ["s2"], status: "done", chars: 1, path: "", preview: "" });
      await first!; });
    expect(result.current.data?.query).toBe("grep");   
    expect(result.current.query).toEqual({ mode: "grep", value: "X" });
  });

  it("没打开运行时不发请求", async () => {
    const spy = vi.spyOn(api, "wfRunWhy");
    const { result } = renderHook(() => useRunWhy("", "/p"));
    await act(async () => { await result.current.ask({ mode: "overview", value: "" }); });
    expect(spy).not.toHaveBeenCalled();
  });

  it("失败时清掉旧数据并给错误文案（不留一份看起来正常的旧结果）", async () => {
    vi.spyOn(api, "wfRunWhy")
      .mockResolvedValueOnce(overview())
      .mockRejectedValueOnce(new Error("运行不存在"));
    const { result } = renderHook(() => useRunWhy("r1", "/p"));

    await act(async () => { await result.current.ask({ mode: "overview", value: "" }); });
    expect(result.current.data).toBeTruthy();

    await act(async () => { await result.current.ask({ mode: "grep", value: "X" }); });
    expect(result.current.error).toContain("运行不存在");
    expect(result.current.data).toBeNull();
  });
});
