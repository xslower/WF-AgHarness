
import { afterEach, describe, expect, it } from "vitest";
import {
  bindWorkflowRunOpener, openWorkflowRunTab, runIdFromResult,
  type WorkflowRunOpenRequest,
} from "./workflowRunTab";

afterEach(() => bindWorkflowRunOpener(null));

describe("openWorkflowRunTab", () => {
  it("没绑定 opener 时调用不抛（面板未打开）", () => {
    expect(() => openWorkflowRunTab({ runId: "r1" })).not.toThrow();
  });

  it("绑定后把请求原样交给 opener", () => {
    const got: WorkflowRunOpenRequest[] = [];
    bindWorkflowRunOpener((r) => got.push(r));
    openWorkflowRunTab({ runId: "r1", workflow: "研报", project: "/p" });
    expect(got).toEqual([{ runId: "r1", workflow: "研报", project: "/p" }]);
  });

  it("解绑后不再触发", () => {
    const got: WorkflowRunOpenRequest[] = [];
    bindWorkflowRunOpener((r) => got.push(r));
    bindWorkflowRunOpener(null);
    openWorkflowRunTab({ runId: "r1" });
    expect(got).toEqual([]);
  });
});

describe("runIdFromResult", () => {
  it("从工具结果尾部取出 run id", () => {
    expect(runIdFromResult("最终输出\n\n[run_id:abc123]")).toBe("abc123");
  });

  it("带下划线/连字符的 id 也认", () => {
    expect(runIdFromResult("[run_id:run_a-b_1]")).toBe("run_a-b_1");
  });

  it("没有标记返回空串（旧消息不该长出按钮）", () => {
    expect(runIdFromResult("最终输出")).toBe("");
    expect(runIdFromResult(undefined)).toBe("");
    expect(runIdFromResult("")).toBe("");
  });

  it("错误 JSON 里的 run_id 不算（前端只认标记，避免误点失败运行）", () => {
    expect(runIdFromResult('{"error":"工作流失败: x","run_id":"zzz"}')).toBe("");
  });
});
