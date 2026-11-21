

import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { installFakeStorage } from "../../test-utils/fakeStorage";
import { scopedStore, SCOPE_TTL_MS } from "./scopedStore";
import { useScopedState, useScopedWidth } from "./useScopedState";
import { dropSession } from "../chat/chatSessionStore";

beforeEach(() => { installFakeStorage(); });

describe("useScopedState 切作用域", () => {
  it("A 改过的值不影响 B，切回 A 原样恢复", () => {
    const { result, rerender } = renderHook(
      ({ scope }) => useScopedState(scope, "ui.showSidebar", true),
      { initialProps: { scope: "sess:a" } });
    act(() => result.current[1](false));
    expect(result.current[0]).toBe(false);

    rerender({ scope: "sess:b" });
    expect(result.current[0]).toBe(true);          

    rerender({ scope: "sess:a" });
    expect(result.current[0]).toBe(false);         
  });

  it("切作用域不会把旧值写进新作用域", () => {
    const { result, rerender } = renderHook(
      ({ scope }) => useScopedState(scope, "ui.swapLayout", false),
      { initialProps: { scope: "sess:a" } });
    act(() => result.current[1](true));          
    expect(scopedStore.read("sess:b", "ui.swapLayout", SCOPE_TTL_MS)).toBeUndefined();

    rerender({ scope: "sess:b" });
    
    expect(result.current[0]).toBe(false);
    expect(scopedStore.read("sess:b", "ui.swapLayout", SCOPE_TTL_MS)).toBe(false);
    expect(scopedStore.read("sess:a", "ui.swapLayout", SCOPE_TTL_MS)).toBe(true);
  });

  it("数值型带范围夹取，脏值回落默认", () => {
    scopedStore.write("sess:x", "ui.composerH", 9999, SCOPE_TTL_MS);
    const { result } = renderHook(() => useScopedWidth("sess:x", "ui.composerH", 72, 48, 600));
    expect(result.current[0]).toBe(72);
  });

  it("删会话时显示态一并清掉，不留下散键", () => {
    scopedStore.write("sess:gone", "ui.showSidebar", false, SCOPE_TTL_MS);
    expect(localStorage.getItem("chat.gone")).not.toBeNull();
    dropSession("gone");
    expect(scopedStore.read("sess:gone", "ui.showSidebar", SCOPE_TTL_MS)).toBeUndefined();
    expect(localStorage.getItem("chat.gone")).toBeNull();
  });
});
