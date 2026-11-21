import type { ApprovalItem } from "../types";
import { getJson, sendJson } from "../client";

export const approvalsApi = {
  approvalsList: () => getJson<ApprovalItem[]>("/api/approvals"),
  approvalDecide: (id: string, approved: boolean) =>
    sendJson<unknown>(`/api/approvals/${id}/decide`, "POST", { approved }),
  approvalDecideHunks: (id: string, approved: boolean, hunks?: number[] | null) =>
    fetch(`/api/approvals/${id}/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved, hunks: hunks ?? null }),
    }).then((r) => r.json()),
};
