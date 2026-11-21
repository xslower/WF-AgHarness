
import { useCallback } from "react";
import { startDrag } from "../../kernel/ui/drag";
import { clamp } from "../../kernel/ui/drag";
import { useScopedWidth } from "../../kernel/ui/useScopedState";
import { clampPanelWidth } from "../../kernel/space/space";


export const LIMITS = {
  list: { min: 180, max: 500, def: 262 },
  main: { min: 320, max: 1200, def: 560 },
} as const;


function sidebarWidth(): number {
  return document.querySelector<HTMLElement>(".sidebar")?.offsetWidth ?? 240;
}

export interface ArtifactLayout {
  listW: number;
  mainW: number;
  onListDrag: (e: React.MouseEvent) => void;
  onLeftEdgeDrag: (e: React.MouseEvent) => void;
  onRightEdgeDrag: (e: React.MouseEvent) => void;
}


export function useArtifactLayout(scope: string, showList: boolean, showMain: boolean): ArtifactLayout {
  
  
  const [mainW, setMainW] = useScopedWidth(scope, "art.mainW", LIMITS.main.def,
    LIMITS.main.min, LIMITS.main.max);
  const [listW, setListW] = useScopedWidth(scope, "art.listW", LIMITS.list.def,
    LIMITS.list.min, LIMITS.list.max);

  const onListDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startList = listW;
    const startMain = mainW;
    startDrag({
      startX: e.clientX,
      onMove: (dx) => {
        const newList = clamp(startList + dx, LIMITS.list.min, LIMITS.list.max);
        setListW(newList);
        
        setMainW(Math.max(LIMITS.main.min, startMain - (newList - startList)));
      },
    });
  }, [listW, mainW]);

  const onLeftEdgeDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const adjustMain = showMain;   
    const startW = adjustMain ? mainW : listW;
    const sidebar = sidebarWidth();
    const artListW = showList ? listW : 0;
    startDrag({
      startX: e.clientX,
      onMove: (dx) => {
        const w = startW - dx;
        if (adjustMain) {
          setMainW(clampPanelWidth(w, window.innerWidth, sidebar, artListW));
        } else {
          const maxList = Math.min(LIMITS.list.max, window.innerWidth - sidebar - 400);
          setListW(clamp(w, LIMITS.list.min, maxList));
        }
      },
    });
  }, [showMain, showList, mainW, listW]);

  const onRightEdgeDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startW = mainW;
    const sidebar = sidebarWidth();
    const artListW = showList ? listW : 0;
    startDrag({
      startX: e.clientX,
      onMove: (dx) => setMainW(
        clampPanelWidth(startW + dx, window.innerWidth, sidebar, artListW)),
    });
  }, [mainW, showList, listW]);

  return { listW, mainW, onListDrag, onLeftEdgeDrag, onRightEdgeDrag };
}
