
import { useCallback, useRef, useState } from "react";

import { api, type BrowseResult } from "../../kernel/api";
import type { DirEntry } from "../../kernel/api/types/artifact";
import { errText } from "../../kernel/ui/errText";

export type { DirEntry };

export interface DirBrowser {
  current: string;
  parent: string;
  dirs: DirEntry[];
  loading: boolean;
  error: string;
  
  open: (path: string) => Promise<BrowseResult | null>;
}

export function useDirBrowse(onError?: (msg: string) => void): DirBrowser {
  const [current, setCurrent] = useState("");
  const [parent, setParent] = useState("");
  const [dirs, setDirs] = useState<DirEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  
  
  
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const open = useCallback(async (path: string): Promise<BrowseResult | null> => {
    setLoading(true);
    try {
      const d = await api.projectBrowse(path);
      setCurrent(d.current);
      setParent(d.parent);
      setDirs(d.dirs);
      setError("");
      return d;
    } catch (e) {
      const msg = errText(e);
      setError(msg);
      onErrorRef.current?.(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { current, parent, dirs, loading, error, open };
}
