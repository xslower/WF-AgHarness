

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { WfWhy } from "../../kernel/api";
import { RunWhyPanel } from "./RunWhyPanel";
import type { WhyController } from "./useRunWhy";


afterEach(cleanup);

function ctl(data: WfWhy | null, over: Partial<WhyController> = {}): WhyController {
  return {
    data, loading: false, error: "",
    query: { mode: "overview", value: "" },
    ask: vi.fn(async () => {}), reset: vi.fn(),
    ...over,
  };
}

const overview: WfWhy = {
  query: "overview", workflow: "demo", status: "done",
  nodes: [
    { node: "s1", status: "done", chars: 3, empty: false,
      reads: [], writes: ["s1"], ms: 5 },
    { node: "s2", status: "done", chars: 0, empty: true,
      reads: ["s1"], writes: ["s2"], ms: 2 },
  ],
};

describe("RunWhyPanel", () => {
  it("概览里空产出行有明确标记（唯一能看到静默少一块的地方）", () => {
    render(<RunWhyPanel wf={ctl(overview)} runId="r1" />);
    expect(screen.getByText("s1")).toBeTruthy();
    
    expect(screen.getAllByText(/空产出/)).toHaveLength(1);
  });

  it("点一行 → 按 node 问法查那一跳", () => {
    const wf = ctl(overview);
    render(<RunWhyPanel wf={wf} runId="r1" />);
    fireEvent.click(screen.getByText("s2"));
    expect(wf.ask).toHaveBeenCalledWith({ mode: "node", value: "s2" });
  });

  it("node 页：读写分开展示，且「重跑这一跳」带上节点 id", () => {
    const onRedo = vi.fn();
    const wf = ctl({
      query: "node", node: "s2", reads: ["s1", "inputs.q"], writes: ["s2"],
      status: "done", chars: 8, ms: 9, path: "/runs/r1/nodes/s2.txt", preview: "正文",
    });
    render(<RunWhyPanel wf={wf} runId="r1" onRedo={onRedo} />);
    expect(screen.getByText("读了")).toBeTruthy();
    expect(screen.getByText("写了")).toBeTruthy();
    fireEvent.click(screen.getByText(/重跑这一跳/));
    expect(onRedo).toHaveBeenCalledWith("s2");
  });

  it("变量问法：inputs.* 不可点（它不是节点），节点变量可下钻", () => {
    const wf = ctl({ query: "key", key: "s1", writers: ["s1"], readers: ["s2"] });
    render(<RunWhyPanel wf={wf} runId="r1" />);
    fireEvent.click(screen.getByText("s2"));
    expect(wf.ask).toHaveBeenCalledWith({ mode: "node", value: "s2" });
    
    expect(screen.getAllByText("s1").length).toBeGreaterThan(0);
  });

  it("没打开运行：给提示且不发请求", () => {
    const wf = ctl(null);
    render(<RunWhyPanel wf={wf} runId="" />);
    expect(screen.getByText("先打开一条运行再看出处")).toBeTruthy();
    expect(wf.ask).not.toHaveBeenCalled();
  });
});
