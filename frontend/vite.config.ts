import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // 后端端口与运行时同源：VITE_BACKEND_PORT，默认 8001
  const env = loadEnv(mode, process.cwd(), "");
  const backendPort = env.VITE_BACKEND_PORT || "8001";
  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5174,
      // Z: 是网络共享，原生 watcher 会 ECONNRESET 崩溃，改用轮询
      watch: { usePolling: true, interval: 500 },
      proxy: {
        "/api": `http://127.0.0.1:${backendPort}`,
        "/ws": { target: `ws://127.0.0.1:${backendPort}`, ws: true },
      },
    },
  };
});
