
import { useEffect } from "react";
import { api } from "../api";
import { alertDialog } from "../ui/dialog";
import { errText } from "../ui/errText";
import type { AppView } from "./view";

export interface UrlState {
  view: AppView;
  curProject: string;
  curId: string | null;
}

interface RestoreArgs {
  setView: (v: AppView) => void;
  setCurProject: (p: string) => void;
  setCurId: (id: string) => void;
  
  loadSession: (s: Awaited<ReturnType<typeof api.getSession>>) => void;
}


function parseHash(): [string, URLSearchParams] {
  const h = location.hash.replace(/^#\/?/, "");
  const [path, qs] = h.split("?");
  return [path, new URLSearchParams(qs || "")];
}


export function useRestoreFromUrl(args: RestoreArgs): void {
  useEffect(() => {
    const { setView, setCurProject, setCurId, loadSession } = args;
    const applyHash = () => {
      const [path, q] = parseHash();
      const proj = q.get("p") || "";
      if (proj) setCurProject(proj);
      if (path === "proj") {
        const target = q.get("path") || proj;
        if (target) setView({ kind: "project", path: target });
        return;
      }
      if (path === "plugin") {
        const id = q.get("id") || "";
        if (id) setView({ kind: "plugin", project: proj, id });
        return;
      }
      if (path === "bot") {
        const id = q.get("id") || "";
        if (id) setView({ kind: "bot", project: proj, id });
        return;
      }
      if (path === "wf") {
        const name = q.get("n") || "";
        if (name) setView({ kind: "workflow", project: proj, name });
        return;
      }
      
      if (path === "" || path === "home") {
        setView({ kind: "home" });
        return;
      }
      setView({ kind: "chat" });


      const sid = q.get("s");
      if (!sid) return;
      setCurId(sid);
      api.getSession(sid).then((x) => {
        if (x.project) setCurProject(x.project);
        loadSession(x);
      }).catch((e) => {
        
        void alertDialog(`会话加载失败：${errText(e)}`);
      });
    };
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
    
    
  }, []);
}


export function useSyncUrl({ view, curProject, curId }: UrlState): void {
  useEffect(() => {
    const q = new URLSearchParams();
    let h: string;
    if (view.kind === "home") {
      h = "#/";
    } else if (view.kind === "project") {
      q.set("path", view.path);
      h = `#/proj?${q.toString()}`;
    } else if (view.kind === "workflow") {
      if (view.project) q.set("p", view.project);
      if (view.name) q.set("n", view.name);
      h = `#/wf?${q.toString()}`;
    } else if (view.kind === "plugin") {
      if (view.project) q.set("p", view.project);
      q.set("id", view.id);
      h = `#/plugin?${q.toString()}`;
    } else if (view.kind === "bot") {
      if (view.project) q.set("p", view.project);
      q.set("id", view.id);
      h = `#/bot?${q.toString()}`;
    } else {
      if (curProject) q.set("p", curProject);
      if (curId) q.set("s", curId);
      h = `#/chat${q.toString() ? "?" + q.toString() : ""}`;
    }
    if (location.hash !== h) history.replaceState(null, "", h);
  }, [view, curProject, curId]);
}

