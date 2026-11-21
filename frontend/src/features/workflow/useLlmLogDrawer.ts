
import { useState } from "react";

import { useScopedState, useScopedWidth } from "../../kernel/ui/useScopedState";

export interface LlmLogDrawer {
  open: boolean;
  setOpen: (v: boolean) => void;
  maximized: boolean;
  setMaximized: (v: boolean) => void;
  width: number;
  setWidth: (v: number) => void;
  
  focusNode: string | null;
  
  openAt: (nodeId: string) => void;
  
  session: string;
  setSession: (v: string) => void;
}

export function useLlmLogDrawer(scope: string): LlmLogDrawer {
  
  const [open, setOpen] = useScopedState<boolean>(scope, "wf.llmLogOpen", false);
  const [maximized, setMaximized] = useScopedState<boolean>(scope, "wf.llmLogMax", false);
  const [width, setWidth] = useScopedWidth(scope, "wf.llmLogW", 620, 360, 1400);
  const [focusNode, setFocusNode] = useState<string | null>(null);
  const [session, setSession] = useState("new");

  return {
    open, setOpen, maximized, setMaximized, width, setWidth,
    focusNode,
    openAt: (nodeId: string) => { setFocusNode(nodeId); setOpen(true); },
    session, setSession,
  };
}
