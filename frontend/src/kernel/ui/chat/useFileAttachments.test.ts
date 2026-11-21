

import { describe, expect, it, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { MAX_ATTACHMENTS, useFileAttachments } from "./useFileAttachments";


function fakeFileReader(result: string) {
  
  const spy = vi.spyOn(globalThis, "FileReader").mockImplementation(function () {
    const r = {
      result,
      onload: null as null | (() => void),
      onerror: null as null | (() => void),
      readAsDataURL() { queueMicrotask(() => r.onload?.()); },
      readAsText() { queueMicrotask(() => r.onload?.()); },
    };
    return r as unknown as FileReader;
  } as unknown as () => FileReader);
  return spy;
}

function file(name: string, type = ""): File {
  return new File(["x"], name, { type });
}

describe("useFileAttachments", () => {
  it("图片走 dataURL，文档走全文，互不串台", async () => {
    const rd = fakeFileReader("data:image/png;base64,AA");
    const { result } = renderHook(() => useFileAttachments());
    act(() => { result.current.addFiles([file("a.png", "image/png")]); });
    await waitFor(() => expect(result.current.images).toEqual(["data:image/png;base64,AA"]));
    expect(result.current.docs).toEqual([]);
    rd.mockRestore();

    const rd2 = fakeFileReader("# report");
    act(() => { result.current.addFiles([file("report.md", "text/markdown")]); });
    await waitFor(() => expect(result.current.docs).toEqual([
      { name: "report.md", text: "# report" },
    ]));
    expect(result.current.images).toHaveLength(1);
    rd2.mockRestore();
  });

  it("不支持的格式不进列表（提示弹窗不影响状态）", () => {
    const { result } = renderHook(() => useFileAttachments());
    act(() => { result.current.addFiles([file("a.exe", "application/octet-stream")]); });
    expect(result.current.images).toEqual([]);
    expect(result.current.docs).toEqual([]);
  });

  it("图片最多 8 个，clear 一次清空两类", async () => {
    const rd = fakeFileReader("data:image/png;base64,AA");
    const { result } = renderHook(() => useFileAttachments());
    act(() => {
      result.current.addFiles(
        Array.from({ length: 20 }, (_, i) => file(`p${i}.png`, "image/png")));
    });
    await waitFor(() => expect(result.current.images.length).toBeLessThanOrEqual(MAX_ATTACHMENTS));
    expect(result.current.images).toHaveLength(MAX_ATTACHMENTS);
    act(() => { result.current.clear(); });
    expect(result.current.images).toEqual([]);
    expect(result.current.docs).toEqual([]);
    rd.mockRestore();
  });
});
