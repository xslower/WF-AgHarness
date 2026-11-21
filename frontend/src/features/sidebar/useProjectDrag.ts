
import { useCallback, useRef, useState } from "react";

export interface ProjectDragState {
  
  dragging: string | null;
  
  dropOn: string | null;
  onDragStart: (e: React.DragEvent<HTMLElement>, path: string) => void;
  onDragOver: (e: React.DragEvent<HTMLElement>, path: string) => void;
  onDragLeave: (path: string) => void;
  onDrop: (e: React.DragEvent<HTMLElement>, path: string) => void;
  onDragEnd: () => void;
}

export function useProjectDrag(
  onMove: (path: string, parent: string) => Promise<boolean>,
): ProjectDragState {
  const [dragging, setDragging] = useState<string | null>(null);
  const [dropOn, setDropOn] = useState<string | null>(null);
  
  
  const dragRef = useRef<string | null>(null);

  const end = useCallback(() => {
    dragRef.current = null;
    setDragging(null);
    setDropOn(null);
  }, []);

  const onDragStart = useCallback((e: React.DragEvent<HTMLElement>, path: string) => {
    dragRef.current = path;
    setDragging(path);
    e.dataTransfer.effectAllowed = "move";
  }, []);

  const onDragOver = useCallback((e: React.DragEvent<HTMLElement>, path: string) => {
    const src = dragRef.current;
    if (!src) return;
    if (src && (path === src || path.startsWith(src + "/"))) return; 
    e.preventDefault();
    e.stopPropagation();
    setDropOn(path);
  }, []);

  const onDragLeave = useCallback((path: string) => {
    setDropOn((d) => (d === path ? null : d));
  }, []);

  const onDrop = useCallback((e: React.DragEvent<HTMLElement>, path: string) => {
    e.preventDefault();
    e.stopPropagation();
    const src = dragRef.current;
    end();
    if (src && path !== src && !path.startsWith(src + "/")) {
      void onMove(src, path);
    }
  }, [end, onMove]);

  return {
    dragging, dropOn,
    onDragStart, onDragOver, onDragLeave, onDrop, onDragEnd: end,
  };
}
