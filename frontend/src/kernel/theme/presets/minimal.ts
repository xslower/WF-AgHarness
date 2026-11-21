import type { ThemeManifest } from "../contracts";
import { MONO, SANS } from "./fonts";


export const minimal: ThemeManifest = {
  id: "minimal",
  name: "极简风",
  description: "无阴影细边框大量留白，类 Vercel/Geist",
  tokens: {
    bg: "#fafafa", bg2: "#ffffff", panel: "#ffffff", panel2: "#f4f4f5",
    border: "#e4e4e7", border2: "#d4d4d8",
    text: "#18181b", dim: "#71717a",
    accent: "#18181b", accent2: "#52525b",
    ok: "#16a34a", warn: "#ca8a04", err: "#dc2626",
    fontFamily: SANS, fontMono: MONO, fontSize: 14,
    radius: 8, borderWidth: 1, spaceUnit: 8,
    shadow: "none",
  },
  layout: { sidebarWidth: 240, artListWidth: 262, chatMaxWidth: 760, density: "comfortable", preset: "focus" },
};
