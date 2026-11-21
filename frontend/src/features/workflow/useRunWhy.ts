
import { useCallback, useRef, useState } from "react";

import { api } from "../../kernel/api";
import type { WfWhy } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";


export interface WhyQuery {
  mode: "overview" | "node" | "key" | "grep";
  
  value: string;
}

export interface WhyController {
  data: WfWhy | null;
  loading: boolean;
  error: string;
  
  query: WhyQuery;
  ask: (q: WhyQuery) => Promise<void>;
  reset: () => void;
}

export function useRunWhy(runId: string, project: string): WhyController {
  const [data, setData] = useState<WfWhy | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState<WhyQuery>({ mode: "overview", value: "" });
  const genRef = useRef(0);

  const ask = useCallback(async (q: WhyQuery) => {
    if (!runId) return;
    const gen = ++genRef.current;
    setQuery(q);
    setLoading(true);
    setError("");
    try {
      const d = await api.wfRunWhy(runId, {
        project,
        node: q.mode === "node" ? q.value : "",
        key: q.mode === "key" ? q.value : "",
        grep: q.mode === "grep" ? q.value : "",
      });
      if (gen !== genRef.current) return;   
      setData(d);
    } catch (e) {
      if (gen !== genRef.current) return;
      setError(errText(e));
      setData(null);
    } finally {
      if (gen === genRef.current) setLoading(false);
    }
  }, [runId, project]);

  const reset = useCallback(() => {
    genRef.current++;
    setData(null);
    setError("");
    setLoading(false);
    setQuery({ mode: "overview", value: "" });
  }, []);

  return { data, loading, error, query, ask, reset };
}
