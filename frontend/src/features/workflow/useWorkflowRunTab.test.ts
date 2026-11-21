

import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import { api } from "../../kernel/api";
import type { WfRun } from "../../kernel/api";
import { useWorkflowRunTab } from "./useWorkflowRunTab";

function runOf(over: Partial<WfRun> = {}): WfRun {
  return {
    id: "r1", workflow: "demo", status: "running",
    started: 1, finished: null, nodes: {}, final: "", error: "",
    ...over,
  } as WfRun;
}

beforeEach(() => { vi.restoreAllMocks(); });

describe("useWorkflowRunTab", () => {
  it("拉一次运行状态，running 时继续轮询、done 后停止", async () => {
    const spy = vi.spyOn(api, "wfRunStatus")
      .mockResolvedValueOnce(runOf())
      .mockResolvedValue(runOf({ status: "done", final: "结果" }));

    const { result } = renderHook(() =>
      useWorkflowRunTab({ runId: "r1", project: "/p" }));

    await waitFor(() => expect(result.current.run?.status).toBe("running"));
    
    await waitFor(() => expect(result.current.run?.status).toBe("done"), { timeout: 3000 });
    const calls = spy.mock.calls.length;
    await new Promise((r) => setTimeout(r, 1500));
    expect(spy.mock.calls.length).toBe(calls);   
  }, 10_000);

  it("运行记录不存在时给错误文案（不是永远空白）", async () => {
    vi.spyOn(api, "wfRunStatus").mockRejectedValue(new Error("404"));
    const { result } = renderHook(() =>
      useWorkflowRunTab({ runId: "gone", project: "/p" }));
    await waitFor(() => expect(result.current.error).toContain("不存在"));
    expect(result.current.run).toBeNull();
  });

  it("中止：乐观置状态 + 调接口 + 重新盯收尾", async () => {
    const status = vi.spyOn(api, "wfRunStatus").mockResolvedValue(runOf());
    const cancel = vi.spyOn(api, "wfRunCancel")
      .mockResolvedValue({ ok: true, status: "cancelled" });

    const { result } = renderHook(() =>
      useWorkflowRunTab({ runId: "r1", project: "/p" }));
    await waitFor(() => expect(result.current.run).toBeTruthy());

    await act(async () => { await result.current.cancel(); });
    expect(cancel).toHaveBeenCalledWith("r1", "/p");
    expect(result.current.msg).toContain("已中止");
    expect(status).toHaveBeenCalled();     
  });

  it("人工闸门：提交选择并重新拉状态", async () => {
    vi.spyOn(api, "wfRunStatus").mockResolvedValue(runOf({
      pending_human: { node_id: "h1", title: "确认", ask: "", show: "",
                       options: ["批准"] },
    }));
    const decide = vi.spyOn(api, "wfHumanDecide")
      .mockResolvedValue({ ok: true, node_id: "h1", choice: "批准" });

    const { result } = renderHook(() =>
      useWorkflowRunTab({ runId: "r1", project: "/p" }));
    await waitFor(() => expect(result.current.run?.pending_human).toBeTruthy());

    await act(async () => { await result.current.decide("批准", "备注"); });
    expect(decide).toHaveBeenCalledWith("r1", "h1", "批准", "备注", "/p");
    expect(result.current.msg).toContain("批准");
  });

  it("没有闸门时 decide 不发请求（点错按钮不该报错）", async () => {
    vi.spyOn(api, "wfRunStatus").mockResolvedValue(runOf());
    const decide = vi.spyOn(api, "wfHumanDecide");
    const { result } = renderHook(() =>
      useWorkflowRunTab({ runId: "r1", project: "/p" }));
    await waitFor(() => expect(result.current.run).toBeTruthy());
    await act(async () => { await result.current.decide("批准", ""); });
    expect(decide).not.toHaveBeenCalled();
  });
});
