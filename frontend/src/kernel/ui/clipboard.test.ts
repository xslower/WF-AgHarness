

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clipboardState, copyText } from "./clipboard";
import { stubClipboard } from "../../test-utils/clipboardMock";

beforeEach(() => {
  stubClipboard("ok");
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("copyText 权限路径", () => {
  it("安全上下文里 Clipboard API 成功 → ok", async () => {
    const { writeText } = stubClipboard("ok");
    const r = await copyText("我发的消息");
    expect(r.ok).toBe(true);
    expect(writeText).toHaveBeenCalledWith("我发的消息");
  });

  it("Clipboard API 抛 NotAllowedError 且兜底也失败 → 给权限申请/恢复指引", async () => {
    stubClipboard("denied", false);
    const r = await copyText("文本");
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.reason).toBe("permission");
      expect(r.hint).toContain("剪贴板");
      expect(r.hint).toContain("网站设置");
      expect(r.hint).toContain("申请");
    }
  });

  it("非安全上下文（http 非 localhost）→ 提示 https/localhost", async () => {
    stubClipboard("insecure", false);
    expect(clipboardState()).toBe("insecure");
    const r = await copyText("文本");
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.reason).toBe("insecure");
      expect(r.hint).toContain("https");
      expect(r.hint).toContain("localhost");
    }
  });

  it("execCommand 兜底成功也算成功（老浏览器）", async () => {
    const { execCommand } = stubClipboard("unavailable", true);
    const r = await copyText("文本");
    expect(r.ok).toBe(true);
    expect(execCommand).toHaveBeenCalledWith("copy");
  });

  it("空文本不申请权限", async () => {
    const r = await copyText("");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toBe("empty");
  });
});
