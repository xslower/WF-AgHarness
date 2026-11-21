
import { describe, expect, it, beforeEach } from "vitest";

import { installFakeStorage } from "../../test-utils/fakeStorage";
import { scopedStore, SCOPE_TTL_MS } from "../../kernel/ui/scopedStore";
import {
  SIDEBAR_DEFAULT_W, SIDEBAR_MAX_W, SIDEBAR_MIN_W, readSidebarWidth,
} from "./useSidebarWidth";

const SCOPE = "sess:a";
const KEY = "ui.sidebarW";

function put(v: unknown): void {
  scopedStore.write(SCOPE, KEY, v, SCOPE_TTL_MS);
}

beforeEach(() => { installFakeStorage(); });

describe("readSidebarWidth", () => {
  it("不同会话各存一份，切会话不串", () => {
    scopedStore.write("sess:a", KEY, 320, SCOPE_TTL_MS);
    scopedStore.write("sess:b", KEY, 460, SCOPE_TTL_MS);
    expect(readSidebarWidth("sess:a")).toBe(320);
    expect(readSidebarWidth("sess:b")).toBe(460);
    expect(readSidebarWidth("sess:c")).toBe(SIDEBAR_DEFAULT_W);
  });

  it("没有存过就用默认宽度", () => {
    expect(readSidebarWidth(SCOPE)).toBe(SIDEBAR_DEFAULT_W);
  });

  it("范围内的值原样采用", () => {
    put(320);
    expect(readSidebarWidth(SCOPE)).toBe(320);
  });

  it("正好等于上下限也算合法", () => {
    put(SIDEBAR_MIN_W);
    expect(readSidebarWidth(SCOPE)).toBe(SIDEBAR_MIN_W);
    put(SIDEBAR_MAX_W);
    expect(readSidebarWidth(SCOPE)).toBe(SIDEBAR_MAX_W);
  });

  it("0 宽回落默认（否则整块侧栏消失）", () => {
    put(0);
    expect(readSidebarWidth(SCOPE)).toBe(SIDEBAR_DEFAULT_W);
  });

  it("超上限回落默认（否则正文被挤没）", () => {
    put(5000);
    expect(readSidebarWidth(SCOPE)).toBe(SIDEBAR_DEFAULT_W);
  });

  it("非数字回落默认", () => {
    put("abc");
    expect(readSidebarWidth(SCOPE)).toBe(SIDEBAR_DEFAULT_W);
  });

  it("空串回落默认", () => {
    put("");
    
    expect(readSidebarWidth(SCOPE)).toBe(SIDEBAR_DEFAULT_W);
  });

  it("负数回落默认", () => {
    put(-100);
    expect(readSidebarWidth(SCOPE)).toBe(SIDEBAR_DEFAULT_W);
  });

  it("小数在范围内时接受（拖拽会给出非整数）", () => {
    put(301.5);
    expect(readSidebarWidth(SCOPE)).toBe(301.5);
  });

  it("记录只落在 chat.<sid> 一个键里，没有全局散键", () => {
    put(320);
    expect(localStorage.getItem("chat.a")).not.toBeNull();
    expect(localStorage.getItem(KEY)).toBeNull();
  });
});
