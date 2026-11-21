import type { ThemeManifest } from "../contracts";
import { MONO } from "./fonts";


export const retroTerminal: ThemeManifest = {
  id: "retro-terminal",
  name: "终端复古",
  description: "等宽字体优先，深绿底荧光绿文字，方角，扫描线感",
  tokens: {
    bg: "#04140a", bg2: "#061c0e", panel: "#0a2413", panel2: "#0e2f19",
    border: "#1c4a2a", border2: "#2a6b3d",
    text: "#7dfc9b", dim: "#3f9e5c",
    accent: "#39ff88", accent2: "#b8ff5c",
    ok: "#39ff88", warn: "#e8ff4a", err: "#ff6b5c",
    fontFamily: MONO, fontMono: MONO, fontSize: 13,
    radius: 0, borderWidth: 1, spaceUnit: 8,
    shadow: "0 0 12px rgba(57,255,136,.18)",
  },
  layout: { sidebarWidth: 232, artListWidth: 262, chatMaxWidth: 0, density: "cozy", preset: "classic" },
};
