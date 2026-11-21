
import { useCallback, useEffect, useRef, useState } from "react";
import type { ProjectNode } from "../api";
import { collectPaths } from "../project/projectTree";

const EXPANDED_KEY = "ui.expanded";

export interface Expansion {
  expanded: Set<string>;
  expand: (path: string) => void;
  toggleExpand: (path: string) => void;
  toggleAll: () => void;
}

export function useExpansion(projTree: ProjectNode | null,
                             refreshWfs: (project: string) => Promise<void> | void): Expansion {
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem(EXPANDED_KEY);
      return saved ? new Set<string>(JSON.parse(saved)) : new Set<string>();
    } catch {
      return new Set<string>();
    }
  });
  
  const firstRun = useRef(localStorage.getItem(EXPANDED_KEY) === null);

  useEffect(() => {
    localStorage.setItem(EXPANDED_KEY, JSON.stringify([...expanded]));
  }, [expanded]);

  
  useEffect(() => {
    if (!projTree || expanded.size === 0) return;
    const all = collectPaths(projTree);
    expanded.forEach((p) => {
      if (all.includes(p)) void refreshWfs(p);
    });
    
    
  }, [projTree]);

  useEffect(() => {
    if (!projTree || !firstRun.current) return;
    firstRun.current = false;
    const all = collectPaths(projTree);
    setExpanded(new Set(all));
    all.forEach((p) => void refreshWfs(p));
  }, [projTree, refreshWfs]);

  const expand = useCallback((path: string) => {
    setExpanded((e) => new Set([...e, path]));
  }, []);

  const toggleExpand = useCallback((path: string) => {
    setExpanded((e) => {
      const n = new Set(e);
      if (n.has(path)) {
        n.delete(path);
      } else {
        n.add(path);
        void refreshWfs(path);      
      }
      return n;
    });
  }, [refreshWfs]);

  const toggleAll = useCallback(() => {
    if (!projTree) return;
    const all = collectPaths(projTree);
    if (all.every((p) => expanded.has(p))) {
      setExpanded(new Set());
      return;
    }
    setExpanded(new Set(all));
    all.forEach((p) => void refreshWfs(p));
  }, [projTree, expanded, refreshWfs]);

  return { expanded, expand, toggleExpand, toggleAll };
}
