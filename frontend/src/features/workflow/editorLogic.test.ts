
import { describe, expect, it, vi } from "vitest";
import { isRunning, makeRunEntries } from "./runEntries";
import { openPanel, togglePanel, type PanelSetters } from "./panelToggles";
import { needsRunDialog, prefillInputs } from "./editorActions";
import type { WorkflowDef } from "../../kernel/api";

const wf = (inputs: WorkflowDef["inputs"] = []): WorkflowDef =>
  ({ name: "wf1", nodes: [], edges: [], inputs } as WorkflowDef);

function deps(over: Partial<Parameters<typeof makeRunEntries>[0]> = {}) {
  return {
    wfName: "wf1",
    projectForRuns: "/p",
    project: "/p",
    inputVals: {},
    parallelMode: "sequential" as const,
    selId: "n1" as string | null,
    flash: vi.fn(),
    save: vi.fn(async () => true),
    ...over,
  };
}

function hooks() {
  return {
    startRun: vi.fn(async () => {}),
    runSingleNode: vi.fn(async () => {}),
    startRunFrom: vi.fn(async () => {}),
  };
}

describe("runEntries.startRun", () => {
  it("没命名时提示且不启动", async () => {
    const h = hooks(); const d = deps({ wfName: "" });
    await makeRunEntries(d, h).startRun();
    expect(d.flash).toHaveBeenCalledWith("先保存工作流再运行");
    expect(h.startRun).not.toHaveBeenCalled();
  });

  it("保存失败时不启动运行", async () => {
    const h = hooks(); const d = deps({ save: vi.fn(async () => false) });
    await makeRunEntries(d, h).startRun();
    expect(d.flash).toHaveBeenCalledWith("保存失败，未启动运行");
    expect(h.startRun).not.toHaveBeenCalled();
  });

  it("保存成功后把运行归属项目（不是编辑项目）传下去", async () => {
    const h = hooks();
    const d = deps({ projectForRuns: "/runtime", project: "/edit" });
    await makeRunEntries(d, h).startRun();
    expect(h.startRun).toHaveBeenCalledWith(expect.objectContaining({
      wfName: "wf1", project: "/runtime",
    }));
  });
});

describe("runEntries 单节点两个入口", () => {
  it("没选中节点时提示，且不保存", async () => {
    const h = hooks(); const d = deps({ selId: null });
    const e = makeRunEntries(d, h);
    await e.runSingleNode();
    await e.startRunFrom();
    expect(d.flash).toHaveBeenCalledWith("先选中节点");
    expect(d.save).not.toHaveBeenCalled();
    expect(h.runSingleNode).not.toHaveBeenCalled();
    expect(h.startRunFrom).not.toHaveBeenCalled();
  });

  it("试运行失败文案与续跑失败文案各自独立（原来抄重复容易串）", async () => {
    const h = hooks();
    await makeRunEntries(deps({ save: vi.fn(async () => false) }), h).runSingleNode();
    await makeRunEntries(deps({ save: vi.fn(async () => false) }), h).startRunFrom();
    expect(h.runSingleNode).not.toHaveBeenCalled();
    expect(h.startRunFrom).not.toHaveBeenCalled();
  });
});

describe("panelToggles", () => {
  const make = () => {
    const mk = () => [true, vi.fn()] as [boolean, ReturnType<typeof vi.fn>];
    return {
      palette: mk(), code: mk(), chat: mk(), inspector: mk(), log: mk(),
    };
  };

  it("按名字翻转对应面板", () => {
    const s = make();
    expect(togglePanel("code", s as unknown as PanelSetters)).toBe(true);
    expect(s.code[1]).toHaveBeenCalledTimes(1);
    expect(s.log[1]).not.toHaveBeenCalled();   
  });

  it("未知面板名什么都不做并返回 false（旧实现会静默开日志）", () => {
    const s = make();
    expect(togglePanel("nope", s as unknown as PanelSetters)).toBe(false);
    for (const k of Object.keys(s)) {
      expect(s[k as keyof typeof s][1]).not.toHaveBeenCalled();
    }
  });

  it("openPanel 可以显式置真/置假", () => {
    const s = make();
    openPanel("inspector", s as unknown as PanelSetters, true);
    expect(s.inspector[1]).toHaveBeenCalledWith(expect.any(Function));
  });
});

describe("editorActions 运行参数", () => {
  it("只有声明了输入项才弹参数窗", () => {
    expect(needsRunDialog(wf())).toBe(false);
    expect(needsRunDialog(wf([{ name: "topic", desc: "", type: "text" }]))).toBe(true);
  });

  it("预填默认值只补空着的项，不覆盖用户已填", () => {
    const w = wf([
      { name: "a", desc: "", type: "text", default: "A" },
      { name: "b", desc: "", type: "text", default: "B" },
    ]);
    expect(prefillInputs(w, { b: "用户填的" })).toEqual({ a: "A", b: "用户填的" });
  });

  it("prefillInputs 不改入参对象", () => {
    const vals = {};
    prefillInputs(wf([{ name: "a", desc: "", type: "text", default: "A" }]), vals);
    expect(vals).toEqual({});
  });
});

describe("isRunning", () => {
  it("只有 running 算在跑", () => {
    expect(isRunning(null)).toBeFalsy();
    expect(isRunning({ status: "running" } as never)).toBe(true);
    expect(isRunning({ status: "done" } as never)).toBe(false);
  });
});
