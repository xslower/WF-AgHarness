
import { useCallback, useState } from "react";

import { api } from "../../kernel/api";
import { confirmDialog } from "../../kernel/ui/dialog";
import { useFlash } from "../../kernel/ui/useFlash";
import { errText } from "../../kernel/ui/errText";

export interface SkillItem {
  name: string;
  
  display?: string;
  desc: string;
  tags: string[];
  lines: number;
  
  source?: "builtin" | "project" | "plugin";
}

export interface ExploreItem {
  fullName: string;
  description: string;
  stars: number;
  url: string;
  rawUrl: string;
  owner: string;
  topics: string[];
}

export type SkillsView = "installed" | "explore";

export const SKILL_PAGE_SIZE = 12;


interface SkillsDetailResp { skills?: SkillItem[] }
interface ExploreResp {
  items?: ExploreItem[];
  total?: number;
  hasMore?: boolean;
  
  degraded?: boolean;
  
  note?: string;
}
interface InstallResp { name?: string }

export function useSkills() {
  const [view, setView] = useState<SkillsView>("installed");
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [url, setUrl] = useState("");
  const [custName, setCustName] = useState("");
  const [busy, setBusy] = useState(false);

  const [query, setQuery] = useState("");
  const [exploreItems, setExploreItems] = useState<ExploreItem[]>([]);
  const [exploreTotal, setExploreTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [degraded, setDegraded] = useState<{ on: boolean; note: string }>({
    on: false, note: "",
  });
  const [installing, setInstalling] = useState("");

  const { msg, setMsg, flash, flashErr } = useFlash(3000);

  const loadInstalled = useCallback(async () => {
    try {
      const r = (await api.skillsDetail()) as SkillsDetailResp;
      setSkills(r.skills ?? []);
    } catch (e) { flashErr(`加载失败: ${e}`); }
  }, [flashErr]);

  const explore = useCallback(async (p = 1) => {
    setBusy(true);
    try {
      const r = (await api.skillsExplore(query.trim(), p, SKILL_PAGE_SIZE)) as ExploreResp;
      setExploreItems(r.items ?? []);
      setExploreTotal(r.total ?? 0);
      setHasMore(r.hasMore ?? false);
      setDegraded({ on: Boolean(r.degraded), note: r.note ?? "" });
      setPage(p);
      setPage(p);
    } catch (e) { flashErr(errText(e)); }
    finally { setBusy(false); }
  }, [query, flashErr]);

  const installFromUrl = async () => {
    const u = url.trim();
    if (!u) { flashErr("请输入 Skill URL"); return; }
    setBusy(true);
    try {
      const r = (await api.skillsInstall(u, custName.trim() || undefined)) as InstallResp;
      flash(`✓ 已安装: ${r.name}`);
      setUrl(""); setCustName("");
      await loadInstalled();
    } catch (e) { flashErr(errText(e)); }
    finally { setBusy(false); }
  };

  const installFromExplore = async (item: ExploreItem) => {
    setInstalling(item.fullName);
    try {
      const r = (await api.skillsInstall(item.rawUrl, item.fullName.replace("/", "-"))) as InstallResp;
      flash(`✓ 已安装: ${r.name}`);
      await loadInstalled();
    } catch (e) {
      
      if (errText(e).includes("409")) flashErr("已安装过，请先删除旧版");
      else flashErr(errText(e));
    }
    finally { setInstalling(""); }
  };

  const remove = async (name: string) => {
    if (!(await confirmDialog({
      title: "删除 Skill", danger: true, okText: "删除",
      message: `确定删除 ${name} ？`,
    }))) return;
    setBusy(true);
    try {
      await api.skillsDelete(name);
      flash(`✓ 已删除: ${name}`);
      await loadInstalled();
    } catch (e) { flashErr(errText(e)); }
    finally { setBusy(false); }
  };

  return {
    
    view, setView,
    
    skills, loadInstalled, remove,
    url, setUrl, custName, setCustName, installFromUrl,
    
    query, setQuery, explore, exploreItems, exploreTotal, page, hasMore,
    degraded, installing, installFromExplore,
    
    busy, msg, setMsg,
  };
}
export type SkillsController = ReturnType<typeof useSkills>;
