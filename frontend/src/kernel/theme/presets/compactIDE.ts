import type { ThemeManifest } from "../contracts";
import { MONO, SANS } from "./fonts";


export const compactIDE: ThemeManifest = {
  id: "compact-ide",
  name: "紧凑工具风",
  description: "小字号高密度，类 VSCode/JetBrains IDE",
  tokens: {
    bg: "#1e1e1e", bg2: "#252526", panel: "#2d2d30", panel2: "#333338",
    border: "#3c3c3c", border2: "#4b4b4b",
    text: "#d4d4d4", dim: "#8a8a8a",
    accent: "#3794ff", accent2: "#c586c0",
    ok: "#89d185", warn: "#cca700", err: "#f14c4c",
    fontFamily: SANS, fontMono: MONO, fontSize: 13,
    radius: 4, borderWidth: 1, spaceUnit: 4,
    shadow: "0 2px 8px rgba(0,0,0,.4)",
  },
  layout: { sidebarWidth: 220, artListWidth: 262, chatMaxWidth: 0, density: "compact", preset: "classic" },
};
