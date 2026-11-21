import type { ThemeManifest } from "../contracts";
import { MONO, SANS } from "./fonts";


export const glassmorphism: ThemeManifest = {
  id: "glassmorphism",
  name: "玻璃拟态",
  description: "半透明面板 backdrop-filter，柔和渐变 accent，大圆角",
  tokens: {
    bg: "#0b1020", bg2: "#101830", panel: "rgba(255,255,255,.08)", panel2: "rgba(255,255,255,.12)",
    border: "rgba(255,255,255,.14)", border2: "rgba(255,255,255,.22)",
    text: "#eef1f8", dim: "#9aa3bd",
    accent: "#7f9bff", accent2: "#b18cff",
    ok: "#5eead4", warn: "#fcd34d", err: "#fb7185",
    fontFamily: SANS, fontMono: MONO, fontSize: 14,
    radius: 16, borderWidth: 1, spaceUnit: 8,
    shadow: "0 8px 32px rgba(8,12,32,.45)",
  },
  layout: { sidebarWidth: 248, artListWidth: 262, chatMaxWidth: 820, density: "comfortable", preset: "split" },
};
