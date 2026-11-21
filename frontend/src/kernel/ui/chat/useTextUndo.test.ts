

import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTextUndo } from "./useTextUndo";


function key(k: string, opts: { ctrl?: boolean; shift?: boolean } = {}) {
  let prevented = false;
  return {
    e: {
      key: k, ctrlKey: !!opts.ctrl, metaKey: false, shiftKey: !!opts.shift,
      preventDefault: () => { prevented = true; },
    } as unknown as React.KeyboardEvent,
    wasPrevented: () => prevented,
  };
}

afterEach(() => { vi.useRealTimers(); });


function typeChars(record: (s: string) => void, ...steps: string[]) {
  vi.useFakeTimers();
  vi.setSystemTime(0);
  for (const s of steps) {
    vi.advanceTimersByTime(600);
    record(s);
  }
}

describe("useTextUndo", () => {
  it("撤销 / 重做按记录顺序回退，且不消费普通按键", () => {
    const { result } = renderHook(() => useTextUndo());
    let text = "";
    const setText = (v: string) => { text = v; };

    act(() => { typeChars(result.current.record, "a", "ab", "abc"); });
    text = "abc";

    const z = key("z", { ctrl: true });
    let consumed = false;
    act(() => { consumed = result.current.handleKey(z.e, setText); });
    expect(consumed).toBe(true);
    expect(z.wasPrevented()).toBe(true);
    expect(text).toBe("ab");

    const y = key("y", { ctrl: true });
    act(() => { result.current.handleKey(y.e, setText); });
    expect(text).toBe("abc");

    const plain = key("a");
    act(() => { expect(result.current.handleKey(plain.e, setText)).toBe(false); });
    expect(plain.wasPrevented()).toBe(false);
  });

  it("Ctrl+Shift+Z 与 Ctrl+Y 同为重做", () => {
    const { result } = renderHook(() => useTextUndo());
    let text = "";
    act(() => { typeChars(result.current.record, "one", "two"); });
    text = "two";
    act(() => { result.current.handleKey(key("z", { ctrl: true }).e, (v) => { text = v; }); });
    expect(text).toBe("one");
    act(() => {
      result.current.handleKey(key("z", { ctrl: true, shift: true }).e,
        (v) => { text = v; });
    });
    expect(text).toBe("two");
  });

  it("500ms 内的连续输入合并成一条撤销记录（这是设计，不是 bug）", () => {
    const { result } = renderHook(() => useTextUndo());
    let text = "abc";
    act(() => {
      vi.useFakeTimers();
      vi.setSystemTime(1000);
      result.current.record("a");
      result.current.record("ab");
      result.current.record("abc");
    });
    act(() => { result.current.handleKey(key("z", { ctrl: true }).e,
      (v) => { text = v; }); });
    expect(text).toBe("");   
  });

  it("在最早的一栈继续撤销不会越界", () => {
    const { result } = renderHook(() => useTextUndo());
    let text = "x";
    act(() => { typeChars(result.current.record, "x"); });
    for (let i = 0; i < 3; i++) {
      act(() => { result.current.handleKey(key("z", { ctrl: true }).e,
        (v) => { text = v; }); });
    }
    expect(text).toBe("");
  });
});
