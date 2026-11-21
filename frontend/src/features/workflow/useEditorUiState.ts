
import { useState } from "react";

export interface EditorUiState {
  
  nameEdit: string | null;
  setNameEdit: (v: string | null) => void;
  
  parallelMenu: boolean;
  setParallelMenu: (v: boolean) => void;
  
  ctxMenu: { x: number; y: number; id: string } | null;
  setCtxMenu: (v: { x: number; y: number; id: string } | null) => void;
  
  selId: string | null;
  setSelId: (v: string | null) => void;
  
  openNodeMenu: (x: number, y: number, id: string) => void;
  
  dismissPopups: () => void;
}

export function useEditorUiState(): EditorUiState {
  const [nameEdit, setNameEdit] = useState<string | null>(null);
  const [parallelMenu, setParallelMenu] = useState(false);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; id: string } | null>(null);
  const [selId, setSelId] = useState<string | null>(null);

  return {
    nameEdit, setNameEdit,
    parallelMenu, setParallelMenu,
    ctxMenu, setCtxMenu,
    selId, setSelId,
    openNodeMenu: (x, y, id) => { setSelId(id); setCtxMenu({ x, y, id }); },
    dismissPopups: () => { setSelId(null); setCtxMenu(null); },
  };
}
