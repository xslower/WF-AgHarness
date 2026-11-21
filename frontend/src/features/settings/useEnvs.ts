
import { useCallback, useRef, useState } from "react";

import { api } from "../../kernel/api";
import type { EnvEntry } from "../../kernel/api";
import { errText } from "../../kernel/ui/errText";
import { useFlash } from "../../kernel/ui/useFlash";

export interface EnvsController {
  found: EnvEntry[];
  pythonEnvs: EnvEntry[];
  nodeEnvs: EnvEntry[];
  bindings: { python: string; node: string };
  bind: (kind: "python" | "node", path: string) => Promise<void>;
  newPath: string;
  setNewPath: (v: string) => void;
  reload: () => Promise<void>;
  createVenv: () => Promise<void>;
  msg: string;
  flash: (t: string, ms?: number) => void;
}

export function useEnvs(): EnvsController {
  const [found, setFound] = useState<EnvEntry[]>([]);
  const [bindings, setBindings] = useState({ python: "", node: "" });
  const [newPath, setNewPath] = useState("");
  const { msg, flash, flashErr } = useFlash(4000);
  
  const bindingsRef = useRef(bindings);
  bindingsRef.current = bindings;
  const bindSeq = useRef(0);

  const reload = useCallback(async () => {
    try {
      const d = await api.envsScan();
      setFound(d.found);
      setBindings(d.bindings);
    } catch (e) {
      flash(`扫描失败：${errText(e)}`);
    }
  }, [flash]);

  const createVenv = async () => {
    const p = newPath.trim();
    if (!p) return;
    flash("创建中…（最长 5 分钟）", 300_000);
    try {
      const r = await api.envsCreateVenv(p);
      flash(r.ok ? `✓ 已创建 ${r.path}（点重新扫描后绑定）` : `失败: ${r.error}`);
    } catch (e) {
      flash(`创建失败：${errText(e)}`);
    }
  };

  const bind = async (kind: "python" | "node", path: string) => {
    const next = { ...bindingsRef.current, [kind]: path };
    bindingsRef.current = next;
    const seq = ++bindSeq.current;
    setBindings(next);                        
    try {
      await api.envsBind(next.python, next.node);
      if (seq === bindSeq.current)
        flash("✓ 已绑定，Agent 的 python/pip/node/npm 命令将自动改写到绑定环境");
    } catch (e) {
      if (seq !== bindSeq.current) return;
      flashErr(`绑定失败：${errText(e)}`);
      const fresh = await api.envsScan().catch(() => null);
      if (fresh && seq === bindSeq.current) setBindings(fresh.bindings);
    }
  };

  return {
    found,
    pythonEnvs: found.filter((e) => e.kind === "python"),
    nodeEnvs: found.filter((e) => e.kind === "node"),
    bindings, bind, newPath, setNewPath, reload, createVenv, msg, flash,
  };
}
