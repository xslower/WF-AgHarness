

import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../../kernel/api";
import type { WfRun } from "../../kernel/api";
import { redoFrom } from "./redoRun";

function runOf(over: Partial<WfRun> = {}): WfRun {
  return { id: "r1", workflow: "demo", status: "done", started: 1,
    finished: 2, nodes: {}, final: "", error: "", ...over } as WfRun;
}

beforeEach(() => { vi.restoreAllMocks(); });

describe("redoFrom", () => {
  it("成功后跟到新运行并刷新历史（否则界面停在旧结果上）", async () => {
    const redo = vi.spyOn(api, "wfRunRedo").mockResolvedValue({ run_id: "r2" });
    const follow = vi.fn(async () => {});
    const refresh = vi.fn(async () => {});
    const flash = vi.fn();

    const ok = await redoFrom({ run: runOf(), project: "/p", flash, follow, refresh },
      "s2", "不满意");

    expect(ok).toBe(true);
    expect(redo).toHaveBeenCalledWith("r1", "s2", "不满意", "/p");
    expect(follow).toHaveBeenCalledWith("r2");     
    expect(refresh).toHaveBeenCalled();
    expect(flash).toHaveBeenLastCalledWith(expect.stringContaining("s2"));
  });

  it("接口报错时不动界面，只出提示", async () => {
    vi.spyOn(api, "wfRunRedo").mockRejectedValue(new Error("节点不存在: nope"));
    const follow = vi.fn(async () => {});
    const flash = vi.fn();

    const ok = await redoFrom({ run: runOf(), project: "/p", flash,
      follow, refresh: async () => {} }, "nope");

    expect(ok).toBe(false);
    expect(follow).not.toHaveBeenCalled();
    expect(flash).toHaveBeenLastCalledWith(expect.stringContaining("节点不存在"));
  });

  it("没运行 / 没节点：说清楚且不发请求（静默 return 就是点了没反应）", async () => {
    const spy = vi.spyOn(api, "wfRunRedo");
    const flash = vi.fn();
    const deps = { project: "/p", flash, follow: async () => {}, refresh: async () => {} };

    expect(await redoFrom({ ...deps, run: null }, "s2")).toBe(false);
    expect(flash).toHaveBeenLastCalledWith(expect.stringContaining("没有可重跑"));

    expect(await redoFrom({ ...deps, run: runOf() }, "")).toBe(false);
    expect(flash).toHaveBeenLastCalledWith(expect.stringContaining("选中"));

    expect(spy).not.toHaveBeenCalled();
  });
});
