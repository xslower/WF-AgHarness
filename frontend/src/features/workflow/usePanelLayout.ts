
import { resizeWidth } from "../../kernel/ui/drag";
import { useScopedWidth } from "../../kernel/ui/useScopedState";

export function usePanelLayout(scope: string) {
  const [codeW, setCodeW] = useScopedWidth(scope, "wf.codeW", 340, 260, 760);
  const [chatW, setChatW] = useScopedWidth(scope, "wf.chatW", 300, 240, 680);
  const [insW, setInsW] = useScopedWidth(scope, "wf.insW", 280, 220, 560);
  
  
  const panelDrag = (setter: (v: number) => void, startW: number, min: number, max: number) =>
    resizeWidth({ width: startW, min, max, edge: "left", setWidth: setter });
  return { codeW, setCodeW, chatW, setChatW, insW, setInsW, panelDrag };
}
