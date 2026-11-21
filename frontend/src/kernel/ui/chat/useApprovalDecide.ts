
import { useCallback } from "react";

import { api } from "../../api";
import type { ApprovalItem } from "../../api";
import { alertDialog } from "../dialog";
import { errText } from "../errText";

export function useApprovalDecide(item: ApprovalItem, onDone: () => void) {
  return useCallback(async (approved: boolean, checkedHunks: number[]) => {
    try {
      if (approved && item.kind === "file" && item.file_diff) {
        
        await api.approvalDecideHunks(item.id, true, checkedHunks);
      } else {
        await api.approvalDecide(item.id, approved);
      }
    } catch (e) {
      void alertDialog(`提交审批失败：${errText(e)}`);
      return;
    }
    onDone();
  }, [item, onDone]);
}
