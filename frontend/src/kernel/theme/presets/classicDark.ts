import type { ThemeManifest } from "../contracts";
import { MONO, SANS } from "./fonts";


export const classicDark: ThemeManifest = {
  id: "classic-dark",
  name: "经典深色",
  description: "延续原版深色观感，间距对齐 8pt 网格",
  tokens: {
    bg: "#0f1115", bg2: "#15181e", panel: "#1a1e26", panel2: "#20252f",
    border: "#2a303c", border2: "#363d4b",
    text: "#e6e9ef", dim: "#8b93a3",
    accent: "#6c8cff", accent2: "#8b6cff",
    ok: "#4ade80", warn: "#fbbf24", err: "#f87171",
    fontFamily: SANS, fontMono: MONO, fontSize: 14,
    radius: 10, borderWidth: 1, spaceUnit: 8,
    shadow: "0 4px 16px rgba(0,0,0,.35)",
  },
  layout: { sidebarWidth: 240, artListWidth: 262, chatMaxWidth: 0, density: "cozy", preset: "classic" },
};
