
import { useState } from "react";

import { api } from "../../kernel/api";
import { alertDialog, confirmDialog } from "../../kernel/ui/dialog";
import { errText } from "../../kernel/ui/errText";


export function parentDir(p: string): string {
  const i = Math.max(p.lastIndexOf("/"), p.lastIndexOf("\\"));
  return i >= 0 ? p.slice(0, i) : "";
}

export interface Clipboard { path: string; op: "cut" | "copy" }

export interface FileCtxActions {
  clipboard: Clipboard | null;
  cut: (path: string) => void;
  copy: (path: string) => void;
  remove: (path: string, name: string) => Promise<void>;
  rename: (path: string, name: string) => Promise<void>;
  paste: (menu: { path: string; isDir: boolean }) => Promise<void>;
}

export function useFileCtxActions(
  project: string,
  onDone: () => void,
): FileCtxActions {
  const [clipboard, setClipboard] = useState<Clipboard | null>(null);

  
  const remove = async (path: string, name: string) => {
    const ok = await confirmDialog({
      title: "移到回收站",
      okText: "移到回收站",
      message: `把 ${name} 移到回收站（.trash，可恢复）？`,
    });
    if (!ok) return;
    try {
      await api.fileDelete(path, project);
    } catch (e) {
      void alertDialog(`删除失败：${errText(e)}`);
      return;
    }
    onDone();
  };

  
  const rename = async (path: string, name: string) => {
    const dir = parentDir(path);
    const next = window.prompt(`重命名 "${name}"`, name);
    if (!next || next === name) return;
    try {
      await api.fileMove(path, `${dir}/${next}`, project);
    } catch (e) {
      void alertDialog(`重命名失败：${errText(e)}`);
      return;
    }
    onDone();
  };

  
  const paste = async (menu: { path: string; isDir: boolean }) => {
    if (!clipboard) return;
    const destDir = menu.isDir ? menu.path : parentDir(menu.path);
    try {
      if (clipboard.op === "cut") await api.fileMove(clipboard.path, destDir, project);
      else await api.fileCopy(clipboard.path, destDir, project);
    } catch (e) {
      void alertDialog(`粘贴失败：${errText(e)}`);
      return;
    }
    setClipboard(null);
    onDone();
  };

  return {
    clipboard,
    cut: (path) => setClipboard({ path, op: "cut" }),
    copy: (path) => setClipboard({ path, op: "copy" }),
    remove, rename, paste,
  };
}
