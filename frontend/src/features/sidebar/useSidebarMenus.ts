
import { useEffect, useState } from "react";

import { menuPosition } from "./menuPos";


export const SESS_MENU_SIZE = { width: 120, height: 74 };

export const PROJ_MENU_SIZE = { width: 140, height: 44 };

export interface SessMenuState {
  id: string;
  x: number;
  y: number;
}

export interface ProjMenuState {
  path: string;
  x: number;
  y: number;
}

function anchor(el: HTMLElement, size: { width: number; height: number }) {
  return menuPosition(
    el.getBoundingClientRect(),
    size,
    { width: window.innerWidth, height: window.innerHeight },
  );
}

export function useSidebarMenus() {
  const [sessMenu, setSessMenu] = useState<SessMenuState | null>(null);
  const [projMenu, setProjMenu] = useState<ProjMenuState | null>(null);

  
  function openSessMenu(e: React.MouseEvent<HTMLElement>, id: string) {
    e.stopPropagation();
    if (sessMenu?.id === id) {
      setSessMenu(null);
      return;
    }
    setSessMenu({ id, ...anchor(e.currentTarget, SESS_MENU_SIZE) });
  }

  function openProjMenu(e: React.MouseEvent<HTMLElement>, path: string) {
    e.stopPropagation();
    if (projMenu?.path === path) {
      setProjMenu(null);
      return;
    }
    setProjMenu({ path, ...anchor(e.currentTarget, PROJ_MENU_SIZE) });
  }

  function closeAll() {
    setSessMenu(null);
    setProjMenu(null);
  }

  
  useEffect(() => {
    if (!sessMenu && !projMenu) return;
    const onDown = (ev: PointerEvent) => {
      const t = ev.target as HTMLElement | null;
      if (t?.closest?.(".sess-menu")) return;   
      closeAll();
    };
    document.addEventListener("pointerdown", onDown);
    window.addEventListener("scroll", closeAll, true);
    window.addEventListener("resize", closeAll);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      window.removeEventListener("scroll", closeAll, true);
      window.removeEventListener("resize", closeAll);
    };
  }, [sessMenu, projMenu]);

  return {
    sessMenu, projMenu, setSessMenu, setProjMenu,
    openSessMenu, openProjMenu, closeAll,
  };
}
