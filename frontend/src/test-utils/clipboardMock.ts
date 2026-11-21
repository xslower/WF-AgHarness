
import { vi } from "vitest";

export type ClipboardMode = "ok" | "denied" | "unavailable" | "insecure";

export function stubClipboard(mode: ClipboardMode, legacyOk = false) {
  Object.defineProperty(window, "isSecureContext", {
    value: mode !== "insecure", configurable: true,
  });
  const writeText = vi.fn(async (_text: string) => {
    if (mode === "denied") throw new DOMException("denied", "NotAllowedError");
  });
  Object.defineProperty(navigator, "clipboard", {
    value: mode === "unavailable" || mode === "insecure"
      ? undefined : { writeText },
    configurable: true,
  });
  Object.defineProperty(navigator, "permissions", {
    value: { query: vi.fn(async () => ({
      state: mode === "denied" ? "denied" : "prompt" })) },
    configurable: true,
  });
  const execCommand = vi.fn(() => legacyOk);
  Object.defineProperty(document, "execCommand", {
    value: execCommand, configurable: true, writable: true,
  });
  return { writeText, execCommand };
}
