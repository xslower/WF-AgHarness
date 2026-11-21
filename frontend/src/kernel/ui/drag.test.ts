import { beforeEach, describe, expect, it, vi } from "vitest";
import { clamp, resizeHeight, resizeWidth, startDrag } from "../../kernel/ui/drag";


function installDom() {
  const handlers = new Map<string, Set<(e: unknown) => void>>();
  const fakeWindow = {
    addEventListener: (t: string, fn: (e: unknown) => void) => {
      if (!handlers.has(t)) handlers.set(t, new Set());
      handlers.get(t)!.add(fn);
    },
    removeEventListener: (t: string, fn: (e: unknown) => void) => {
      handlers.get(t)?.delete(fn);
    },
  };
  const fakeDocument = { body: { style: { cursor: "" } } };
  (globalThis as any).window = fakeWindow;
  (globalThis as any).document = fakeDocument;
  const emit = (type: string, ev: Record<string, unknown>) => {
    for (const fn of [...(handlers.get(type) ?? [])]) fn(ev);
  };
  const count = (type: string) => handlers.get(type)?.size ?? 0;
  return { emit, count, fakeDocument };
}

let dom: ReturnType<typeof installDom>;
beforeEach(() => { dom = installDom(); });

describe("clamp", () => {
  it("落在区间内", () => {
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(-1, 0, 10)).toBe(0);
    expect(clamp(11, 0, 10)).toBe(10);
  });
});

describe("startDrag", () => {
  it("按位移回调，而不是绝对坐标", () => {
    const onMove = vi.fn();
    startDrag({ startX: 100, startY: 50, onMove });
    dom.emit("mousemove", { clientX: 130, clientY: 20 });
    expect(onMove).toHaveBeenCalledWith(30, -30, expect.anything());
  });

  it("拖拽期间给 body 设光标，默认 col-resize", () => {
    startDrag({ startX: 0, onMove: () => {} });
    expect(dom.fakeDocument.body.style.cursor).toBe("col-resize");
  });

  it("可以指定光标（面板拖动用 move）", () => {
    startDrag({ startX: 0, cursor: "move", onMove: () => {} });
    expect(dom.fakeDocument.body.style.cursor).toBe("move");
  });

  it("mouseup 后解绑两个监听、复原光标并调 onEnd", () => {
    const onEnd = vi.fn();
    startDrag({ startX: 0, onMove: () => {}, onEnd });
    expect(dom.count("mousemove")).toBe(1);
    dom.emit("mouseup", {});
    expect(dom.count("mousemove")).toBe(0);
    expect(dom.count("mouseup")).toBe(0);
    expect(dom.fakeDocument.body.style.cursor).toBe("");
    expect(onEnd).toHaveBeenCalledTimes(1);
  });

  it("结束后再动鼠标不会再触发 onMove（避免松手后还在拖）", () => {
    const onMove = vi.fn();
    startDrag({ startX: 0, onMove });
    dom.emit("mouseup", {});
    dom.emit("mousemove", { clientX: 50, clientY: 0 });
    expect(onMove).not.toHaveBeenCalled();
  });
});

describe("resizeWidth", () => {
  it("拖左缘：向左拖变宽", () => {
    const setWidth = vi.fn();
    const onDown = resizeWidth({ width: 300, min: 200, max: 600, edge: "left", setWidth });
    onDown({ clientX: 400, preventDefault: () => {} } as never);
    dom.emit("mousemove", { clientX: 350, clientY: 0 });
    expect(setWidth).toHaveBeenCalledWith(350);
  });

  it("拖右缘：向右拖变宽", () => {
    const setWidth = vi.fn();
    const onDown = resizeWidth({ width: 300, min: 200, max: 600, edge: "right", setWidth });
    onDown({ clientX: 400, preventDefault: () => {} } as never);
    dom.emit("mousemove", { clientX: 460, clientY: 0 });
    expect(setWidth).toHaveBeenCalledWith(360);
  });

  it("受最小/最大宽度约束", () => {
    const setWidth = vi.fn();
    const onDown = resizeWidth({ width: 300, min: 250, max: 320, edge: "right", setWidth });
    onDown({ clientX: 0, preventDefault: () => {} } as never);
    dom.emit("mousemove", { clientX: 10_000, clientY: 0 });
    expect(setWidth).toHaveBeenLastCalledWith(320);
    dom.emit("mousemove", { clientX: -10_000, clientY: 0 });
    expect(setWidth).toHaveBeenLastCalledWith(250);
  });

  it("按下时阻止默认行为（否则会选中文字）", () => {
    const prevent = vi.fn();
    const onDown = resizeWidth({ width: 300, min: 200, max: 600, setWidth: () => {} });
    onDown({ clientX: 0, preventDefault: prevent } as never);
    expect(prevent).toHaveBeenCalled();
  });
});

describe("resizeHeight", () => {
  
  
  it("拖上缘：往上拖变高", () => {
    const setHeight = vi.fn();
    const onDown = resizeHeight({ height: 220, min: 120, max: 640, edge: "top", setHeight });
    onDown({ clientX: 0, clientY: 500, preventDefault: () => {} } as never);
    dom.emit("mousemove", { clientX: 0, clientY: 430 });
    expect(setHeight).toHaveBeenCalledWith(290);
  });

  it("拖下缘：往下拖变高", () => {
    const setHeight = vi.fn();
    const onDown = resizeHeight({ height: 220, min: 120, max: 640, edge: "bottom", setHeight });
    onDown({ clientX: 0, clientY: 100, preventDefault: () => {} } as never);
    dom.emit("mousemove", { clientX: 0, clientY: 160 });
    expect(setHeight).toHaveBeenCalledWith(280);
  });

  it("横向位移不影响高度", () => {
    const setHeight = vi.fn();
    const onDown = resizeHeight({ height: 220, min: 120, max: 640, setHeight });
    onDown({ clientX: 0, clientY: 500, preventDefault: () => {} } as never);
    dom.emit("mousemove", { clientX: 999, clientY: 500 });
    expect(setHeight).toHaveBeenCalledWith(220);
  });

  it("受上下限约束，且光标是 row-resize", () => {
    const setHeight = vi.fn();
    const onDown = resizeHeight({ height: 220, min: 120, max: 640, setHeight });
    onDown({ clientX: 0, clientY: 500, preventDefault: () => {} } as never);
    expect(dom.fakeDocument.body.style.cursor).toBe("row-resize");
    dom.emit("mousemove", { clientX: 0, clientY: -10_000 });
    expect(setHeight).toHaveBeenLastCalledWith(640);
    dom.emit("mousemove", { clientX: 0, clientY: 10_000 });
    expect(setHeight).toHaveBeenLastCalledWith(120);
  });
});
