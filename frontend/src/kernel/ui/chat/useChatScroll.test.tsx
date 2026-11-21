

import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChatScroll } from "./useChatScroll";
import { readField } from "../../../kernel/chat/chatSessionStore";
import type { ChatMessage } from "../../../kernel/api";

beforeAll(() => {
  Element.prototype.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});

beforeEach(() => {
  localStorage.clear();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

const msg = (t: string): ChatMessage => ({ role: "user", content: t });


const MESSAGES: ChatMessage[] = [msg("hi")];


function fakeScroller(): React.RefObject<HTMLDivElement> {
  const el = document.createElement("div");
  let top = 0;
  Object.defineProperty(el, "scrollTop", {
    get: () => top,
    set: (v: number) => { top = v; },
    configurable: true,
  });
  Object.defineProperty(el, "scrollHeight", { value: 2000, configurable: true });
  Object.defineProperty(el, "clientHeight", { value: 500, configurable: true });
  return { current: el } as React.RefObject<HTMLDivElement>;
}

function mount(scrollRef: React.RefObject<HTMLDivElement>, sessionId: string | null) {
  const stickBottomRef = { current: true };
  return renderHook(
    ({ sid }: { sid: string | null }) => useChatScroll({
      scrollRef,
      stickBottomRef,
      sessionId: sid,
      messages: MESSAGES,
      liveCount: 0,
      onReachTop: () => {},
    }),
    { initialProps: { sid: sessionId } },
  );
}

describe("useChatScroll 滚动位置落盘", () => {
  it("滚动后 250ms 写进当前会话的分区", () => {
    const ref = fakeScroller();
    const { result } = mount(ref, "s-a");

    ref.current!.scrollTop = 1200;
    act(() => { result.current.onScroll(); });
    act(() => { vi.advanceTimersByTime(300); });

    expect(readField("s-a", "scroll", 0)).toBe(1200);
  });

  it("节流窗口内切会话：不许把新会话的位置写进旧分区（也不许反过来）", () => {
    const ref = fakeScroller();
    const { result, rerender } = mount(ref, "s-a");

    
    ref.current!.scrollTop = 1200;
    act(() => { result.current.onScroll(); });

    
    rerender({ sid: "s-b" });
    ref.current!.scrollTop = 300;
    act(() => { result.current.onScroll(); });

    act(() => { vi.advanceTimersByTime(600); });

    
    
    expect(readField("s-a", "scroll", 0)).toBe(1200);
    expect(readField("s-b", "scroll", 0)).toBe(300);
  });

  it("切会话时丢掉排队中的写盘（那次滚动属于旧会话，已无意义）", () => {
    const ref = fakeScroller();
    const { result, rerender } = mount(ref, "s-a");

    ref.current!.scrollTop = 1200;
    act(() => { result.current.onScroll(); });
    rerender({ sid: "s-b" });
    act(() => { vi.advanceTimersByTime(600); });

    
    expect(readField("s-b", "scroll", 0)).toBe(0);
    expect(readField("s-a", "scroll", 0)).toBe(1200);
  });
});
