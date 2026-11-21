
import { useEffect, useRef, useState } from "react";

import type { WfRunFile } from "../../kernel/api";
import { previewTab } from "../artifacts/filePreview";
import type { Tab, UrlBarState } from "../../kernel/ui/artifacts/types";

export interface RunFileTabs extends UrlBarState {
  tabs: Tab[];
  active: string | null;
  setActive: (key: string | null) => void;
  cur: Tab | null;
  error: string;
  closeTab: (key: string) => void;
  patchTab: (key: string, patch: Partial<Tab>) => void;
  
  saveTab: () => void;
}

export function useRunFileTabs(file: WfRunFile | null): RunFileTabs {
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [showUrlBar, setShowUrlBar] = useState(false);

  
  const tabsRef = useRef(tabs);
  tabsRef.current = tabs;

  useEffect(() => {
    if (!file) return;
    const key = file.path;
    setError("");
    
    if (tabsRef.current.some((t) => t.key === key)) { setActive(key); return; }
    let alive = true;
    previewTab(key)
      .then((tab) => {
        if (!alive) return;
        setTabs((ts) => (ts.some((t) => t.key === tab.key) ? ts : [...ts, tab]));
        setActive(tab.key);
      })
      .catch((e: unknown) => {
        if (alive) setError(`打不开 ${file.rel || file.name}：${(e as Error)?.message ?? e}`);
      });
    return () => { alive = false; };
  }, [file]);   

  const openUrl = () => {
    let u = urlInput.trim();
    if (!u) return;
    if (!/^https?:\/\
    setTabs((ts) => (ts.some((t) => t.key === u) ? ts
      : [...ts, { key: u, title: u.replace(/^https?:\/\
    setActive(u);
    setUrlInput("");
    setShowUrlBar(false);
  };

  const closeTab = (key: string) => {
    setTabs((ts) => {
      const rest = ts.filter((t) => t.key !== key);
      if (active === key) setActive(rest[rest.length - 1]?.key ?? null);
      return rest;
    });
  };

  const patchTab = (key: string, patch: Partial<Tab>) =>
    setTabs((ts) => ts.map((t) => (t.key === key ? { ...t, ...patch } : t)));

  const cur = active ? tabs.find((t) => t.key === active) ?? null : null;

  return {
    tabs, active, setActive, cur, error,
    urlInput, setUrlInput, showUrlBar, setShowUrlBar,
    openUrl, closeTab, patchTab, saveTab: () => {},
  };
}
