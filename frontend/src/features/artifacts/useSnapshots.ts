
import { useMemo } from "react";

import { api } from "../../kernel/api";
import type { Checkpoint } from "../../kernel/api";
import { confirmDialog } from "../../kernel/ui/dialog";
import { errText } from "../../kernel/ui/errText";

export interface Snapshots {
  refresh: () => Promise<void>;
  create: () => Promise<void>;
  restore: (c: Checkpoint) => Promise<void>;
}

export function useSnapshots(
  project: string,
  setCks: (v: Checkpoint[]) => void,
  onError: (msg: string) => void,
): Snapshots {
  return useMemo(() => {
    const scope = project || undefined;

    const refresh = async () => {
      try {
        setCks(await api.ckList(scope));
      } catch (e) {
        onError(`读取快照失败：${errText(e)}`);
      }
    };

    const create = async () => {
      try {
        await api.ckCreate("手动快照", scope);
      } catch (e) {
        onError(`创建快照失败：${errText(e)}`);
        return;
      }
      await refresh();
    };

    const restore = async (c: Checkpoint) => {
      if (!(await confirmDialog({
        title: "回滚快照", danger: true, okText: "回滚",
        message: `回滚到 ${c.message}？之后的改动会丢失。`,
      }))) return;
      try {
        await api.ckRestore(c.sha, scope);
      } catch (e) {
        onError(`回滚失败：${errText(e)}`);
        return;
      }
      await refresh();
    };

    return { refresh, create, restore };
  }, [project, setCks, onError]);
}
