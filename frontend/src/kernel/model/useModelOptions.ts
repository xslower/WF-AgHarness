
import { useEffect, useState } from "react";

import { api } from "../api";
import type { ModelOption } from "./modelSpec";
import { modelOptions } from "./modelSpec";


const FALLBACK: ModelOption[] = [{ value: "parent", label: "父队列" }];

export function useModelOptions(): ModelOption[] {
  const [opts, setOpts] = useState<ModelOption[]>(FALLBACK);
  useEffect(() => {
    let alive = true;
    api.getConfig()
      .then((c) => { if (alive) setOpts(modelOptions(c)); })
      .catch(() => {  });
    return () => { alive = false; };
  }, []);
  return opts;
}
