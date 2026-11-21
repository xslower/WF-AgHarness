import type { ThemeManifest } from "../contracts";
import { MONO, SANS } from "./fonts";


export const modernAdmin: ThemeManifest = {
  id: "modern-admin",
  name: "现代中后台",
  description: "借鉴 Ant Design + Chakra：8pt 间距节奏、统一图标按钮、清晰视觉层级",
  tokens: {
    bg: "#f0f2f5", bg2: "#ffffff", panel: "#ffffff", panel2: "#f5f7fa",
    border: "#e5e7eb", border2: "#d1d5db",
    text: "#1f2937", dim: "#6b7280",
    accent: "#2563eb", accent2: "#7c3aed",
    ok: "#16a34a", warn: "#d97706", err: "#dc2626",
    fontFamily: SANS, fontMono: MONO, fontSize: 14,
    radius: 8, borderWidth: 1, spaceUnit: 8,
    shadow: "0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.04)",
  },
  layout: { sidebarWidth: 248, artListWidth: 262, chatMaxWidth: 880, density: "cozy", preset: "split" },
};
