
import { useCallback, useEffect, useRef, useState } from "react";
import { scopedStore, SCOPE_TTL_MS } from "./scopedStore";


function withDefaults<T>(fallback: T, saved: T | undefined): T {
  if (saved === undefined) return fallback;
  const isObj = (v: unknown): v is Record<string, unknown> =>
    !!v && typeof v === "object" && !Array.isArray(v);
  if (isObj(fallback) && isObj(saved)) return { ...fallback, ...saved } as T;
  return saved;
}

export function useScopedState<T>(scope: string, name: string, fallback: T) {
  
  
  
  
  const [state, setState] = useState(() => ({
    scope,
    value: withDefaults(fallback, scopedStore.read<T>(scope, name, SCOPE_TTL_MS)),
  }));
  const cur = state.scope === scope ? state : {
    scope,
    value: withDefaults(fallback, scopedStore.read<T>(scope, name, SCOPE_TTL_MS)),
  };
  const value = cur.value;
  const setValue: React.Dispatch<React.SetStateAction<T>> = useCallback((next) => {
    setState((s) => ({
      scope: s.scope,
      value: typeof next === "function"
        ? (next as (prev: T) => T)(s.value) : next,
    }));
    
    
  }, []);

  
  useEffect(() => {
    if (state.scope !== scope) setState(cur);
    
  }, [scope, state.scope]);

  useEffect(() => {
    scopedStore.write(scope, name, value, SCOPE_TTL_MS);
  }, [scope, name, value]);

  
  const clear = useCallback(() => {
    scopedStore.clearScope(scope);
    setValue(fallback);
    
  }, [scope]);

  return [value, setValue, clear] as const;
}


export function useScopedWidth(scope: string, name: string, fallback: number,
                               min: number, max: number) {
  const [raw, setRaw] = useScopedState<number>(scope, name, fallback);
  const value = typeof raw === "number" && Number.isFinite(raw)
    && raw >= min && raw <= max ? raw : fallback;
  const clamp = useCallback((v: number) => Math.max(min, Math.min(max, v)), [min, max]);
  return [value, setRaw, clamp] as const;
}
