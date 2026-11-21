
import { useCallback, useRef, useState } from "react";
import { api } from "../../kernel/api";
import { useScopedState } from "../../kernel/ui/useScopedState";


export interface TreeNode {
  path: string;
  
  name?: string;
  isDir?: boolean;
  children?: TreeNode[];
  [k: string]: unknown;
}

export interface FileTreeState {
  tree: TreeNode[];
  error: string;
  loading: boolean;
  
  reset: (project: string) => void;
  
  load: (project: string, force?: boolean) => Promise<void>;
  
  toggleDir: (project: string, path: string) => void;
  expandedDirs: Set<string>;
}


export function updateNodeDeep(
  nodes: TreeNode[], path: string, patch: (n: TreeNode) => TreeNode,
): TreeNode[] {
  let hit = false;
  const next = nodes.map((n) => {
    if (n.path === path) { hit = true; return patch(n); }
    if (n.children?.length) {
      const kids = updateNodeDeep(n.children, path, patch);
      
      if (kids !== n.children) { hit = true; return { ...n, children: kids }; }
    }
    return n;
  });
  return hit ? next : nodes;
}

export function useFileTree(scope: string): FileTreeState {
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedArr, setExpandedArr] = useScopedState<string[]>(scope, "art.expandedDirs", []);
  const expandedDirs = new Set(expandedArr);

  
  const cache = useRef<Map<string, TreeNode[]>>(new Map());
  
  const latest = useRef("");
  
  const inflight = useRef<Set<string>>(new Set());

  const reset = useCallback((project: string) => {
    latest.current = project;
    setTree(project ? (cache.current.get(project) ?? []) : []);
    setError("");
  }, []);

  const load = useCallback(async (project: string, force = false) => {
    if (!project) return;
    latest.current = project;
    const cached = cache.current.get(project);
    if (cached) setTree(cached);
    else if (force) setTree([]);
    setLoading(!cached);
    try {
      const d: unknown = await api.fileTree(project);
      if (!Array.isArray(d)) throw new Error("返回格式异常");
      cache.current.set(project, d as TreeNode[]);
      if (latest.current !== project) return;      
      setTree(d as TreeNode[]);
      setError("");
    } catch (e) {
      if (latest.current !== project) return;
      setError(String((e as Error)?.message ?? e));
    } finally {
      if (latest.current === project) setLoading(false);
    }
  }, []);

  const toggleDir = useCallback((project: string, path: string) => {
    const willExpand = !expandedDirs.has(path);
    setExpandedArr((prev) => {
      const n = new Set(prev);
      if (willExpand) n.add(path);
      else n.delete(path);
      return [...n];
    });
    if (!willExpand || !project) return;
    
    if (inflight.current.has(path)) return;
    inflight.current.add(path);
    void api.fileTreeChildren(project, path).then((kids) => {
      if (!Array.isArray(kids)) return;
      setTree((prev) => {
        const next = updateNodeDeep(prev, path, (n) => ({ ...n, children: kids as TreeNode[] }));
        cache.current.set(project, next);
        return next;
      });
    }).catch(() => {  })
      .finally(() => { inflight.current.delete(path); });
  }, [expandedDirs, setExpandedArr]);

  return { tree, error, loading, reset, load, toggleDir, expandedDirs };
}
