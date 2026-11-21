
import { afterEach, describe, expect, it } from "vitest";
import { backendWsUrl, resolveBackendPort } from "./env";

const setLoc = (loc: { hostname: string; port: string; protocol: string }) => {
  (globalThis as { location?: unknown }).location = loc;
};

afterEach(() => {
  delete (globalThis as { location?: unknown }).location;
});

describe("resolveBackendPort", () => {
  it("页面带了端口就用页面端口（换端口部署 / 反向代理）", () => {
    setLoc({ hostname: "127.0.0.1", port: "8097", protocol: "http:" });
    expect(resolveBackendPort()).toBe("8097");
  });

  it("页面没带端口时按协议回落 80/443", () => {
    setLoc({ hostname: "example.com", port: "", protocol: "http:" });
    expect(resolveBackendPort()).toBe("80");
    setLoc({ hostname: "example.com", port: "", protocol: "https:" });
    expect(resolveBackendPort()).toBe("443");
  });
});

describe("backendWsUrl", () => {
  it("端口跟随页面，而不是构建期常量（8001）", () => {
    setLoc({ hostname: "127.0.0.1", port: "8097", protocol: "http:" });
    expect(backendWsUrl("/ws/abc")).toBe("ws://127.0.0.1:8097/ws/abc");
  });

  it("https 页面用 wss", () => {
    setLoc({ hostname: "127.0.0.1", port: "8443", protocol: "https:" });
    expect(backendWsUrl("/ws/events")).toBe("wss://127.0.0.1:8443/ws/events");
  });

  it("远程访问沿用当前主机名（不强行 127.0.0.1）", () => {
    setLoc({ hostname: "192.168.1.10", port: "8001", protocol: "http:" });
    expect(backendWsUrl("/ws/x")).toBe("ws://192.168.1.10:8001/ws/x");
  });

  it("localhost 归一到 127.0.0.1", () => {
    setLoc({ hostname: "localhost", port: "8001", protocol: "http:" });
    expect(backendWsUrl("/ws/x")).toBe("ws://127.0.0.1:8001/ws/x");
  });
});
