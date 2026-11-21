import type { ThemeManifest } from "../contracts";
import { MONO, SANS } from "./fonts";


export const lightModern: ThemeManifest = {
  id: "light-modern",
  name: "浅色现代",
  description: "白底大圆角柔和阴影，类 Linear/Notion 风格",
  tokens: {
    bg: "#f7f8fa", bg2: "#ffffff", panel: "#ffffff", panel2: "#f0f2f5",
    border: "#e3e6eb", border2: "#d3d8e0",
    text: "#1d2129", dim: "#6b7280",
    accent: "#4f6ef7", accent2: "#7c5cf0",
    ok: "#16a34a", warn: "#d97706", err: "#dc2626",
    fontFamily: SANS, fontMono: MONO, fontSize: 14,
    radius: 12, borderWidth: 1, spaceUnit: 8,
    shadow: "0 2px 12px rgba(29,33,41,.08)",
  },
  layout: { sidebarWidth: 250, artListWidth: 262, chatMaxWidth: 860, density: "comfortable", preset: "focus" },
};
