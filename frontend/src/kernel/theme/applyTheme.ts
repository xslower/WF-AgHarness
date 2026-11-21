
import type { ThemeLayout, ThemeManifest, ThemeTokens } from "./contracts";


export function tokensToCSSVars(t: ThemeTokens): Record<string, string> {
  return {
    "--bg": t.bg, "--bg2": t.bg2, "--panel": t.panel, "--panel2": t.panel2,
    "--border": t.border, "--border2": t.border2,
    "--text": t.text, "--dim": t.dim,
    "--accent": t.accent, "--accent2": t.accent2,
    "--ok": t.ok, "--warn": t.warn, "--err": t.err,
    "--font-family": t.fontFamily,
    "--mono": t.fontMono,
    "--font-size": `${t.fontSize}px`,
    "--radius": `${t.radius}px`,
    "--bw": `${t.borderWidth}px`,
    "--space": `${t.spaceUnit}px`,
    "--shadow": t.shadow,
  };
}


export const DENSITY_FACTOR: Record<ThemeLayout["density"], { lh: number; pad: number }> = {
  compact: { lh: 1.4, pad: 0.75 },
  cozy: { lh: 1.65, pad: 1 },
  comfortable: { lh: 1.85, pad: 1.35 },
};

export function applyTheme(theme: ThemeManifest): void {
  const root = document.documentElement;
  for (const [k, v] of Object.entries(tokensToCSSVars(theme.tokens))) {
    root.style.setProperty(k, v);
  }
  root.style.setProperty("--art-list-w", `${theme.layout.artListWidth}px`);
  root.setAttribute("data-density", theme.layout.density);
  root.setAttribute("data-theme", theme.id);
}

export function getTheme(id: string, themes: ThemeManifest[]): ThemeManifest {
  return themes.find((t) => t.id === id) ?? themes[0];
}
