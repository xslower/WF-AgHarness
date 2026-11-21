
import { useCallback, useEffect, useRef, useState } from "react";

export function readStored<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    const v = JSON.parse(raw) as T;
    return v === null || v === undefined ? fallback : v;
  } catch {
    return fallback;          
  }
}

export function writeStored<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    
  }
}

export function useLocalState<T>(key: string, fallback: T) {
  const [value, setValue] = useState<T>(() => readStored(key, fallback));
  const keyRef = useRef(key);
  keyRef.current = key;
  useEffect(() => { writeStored(key, value); }, [key, value]);
  return [value, setValue] as const;
}


function readNumeric(key: string, fallback: number): number {
  const v = readStored<unknown>(key, fallback);
  if (typeof v === "number") return v;
  if (typeof v === "string" && v.trim() && Number.isFinite(Number(v))) return Number(v);
  return fallback;
}


export function useLocalWidth(key: string, fallback: number, min: number, max: number) {
  const [value, setValue] = useState<number>(() => {
    const v = readNumeric(key, fallback);
    return Number.isFinite(v) && v >= min && v <= max ? v : fallback;
  });
  useEffect(() => {
    writeStored(key, Math.max(min, Math.min(max, value)));
  }, [key, value, min, max]);
  const clamp = useCallback((v: number) => Math.max(min, Math.min(max, v)), [min, max]);
  return [value, setValue, clamp] as const;
}
