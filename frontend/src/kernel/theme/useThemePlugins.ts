
import { useEffect, useState } from "react";
import { api } from "../api";
import { createThemeRegistry, normalizeExternalTheme, themeRegistry } from "./registry";
import { applyTheme } from "./applyTheme";

const THEME_KEY = "ui.plugin";
const DEFAULT_THEME_ID = "classic-dark";

export function useThemePlugins() {
  const [themeId, setThemeId] = useState(
    () => localStorage.getItem(THEME_KEY) || DEFAULT_THEME_ID);
  const [registry, setRegistry] = useState(() => themeRegistry);
  const theme = registry.get(themeId) ?? registry.all()[0];

  
  useEffect(() => {
    let alive = true;
    api.themes()
      .then((r) => {
        if (!alive) return;
        const fallback = themeRegistry.all()[0];
        const extra = r.themes.flatMap((t) => {
          try {
            const normalized = normalizeExternalTheme(t, fallback);
            return normalized.id ? [normalized] : [];
          } catch {
            return [];
          }
        });
        const merged = createThemeRegistry(extra);
        setRegistry(merged);
        setThemeId((id) => (merged.get(id) ? id : merged.all()[0].id));
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(THEME_KEY, themeId);
  }, [themeId, theme]);

  return { themeId, setThemeId, registry, theme };
}
