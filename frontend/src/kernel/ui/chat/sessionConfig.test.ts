
import { beforeEach, describe, expect, it } from "vitest";

import {
  readPolicyPref, writePolicyPref, readPrefs, patchPrefs,
} from "../../chat/sessionPrefs";
import { makePayload } from "./chatPayload";
import { installFakeStorage } from "../../../test-utils/fakeStorage";

beforeEach(() => { installFakeStorage(); });

describe("安全档位按会话隔离", () => {
  it("不同 sid 各自独立，切会话不串", () => {
    writePolicyPref("a", "yolo");
    writePolicyPref("b", "review");
    expect(readPolicyPref("a")).toBe("yolo");
    expect(readPolicyPref("b")).toBe("review");
    expect(readPolicyPref("c")).toBe("");       
  });

  it("与其它 prefs 字段共存，patch 只改 policy", () => {
    patchPrefs("a", { model: "p1/m1", plan: "1" });
    writePolicyPref("a", "workspace");
    expect(readPrefs("a")).toEqual({
      model: "p1/m1", plan: "1", policy: "workspace",
    });
    expect(readPolicyPref("a")).toBe("workspace");
  });
});

describe("档位随每条消息 payload 下发", () => {
  const base = { body: "hi", images: [], audio: "", attachments: [] };

  it("显式传了就带上（后端不再读项目 kv）", () => {
    const p = makePayload({ ...base, policy: "yolo", model: "parent" }, "q1");
    expect(p.policy).toBe("yolo");
  });

  it("没选过时带空串，由后端回落默认档", () => {
    const p = makePayload(base, "q1");
    expect(p.policy).toBe("");
  });

  it("model 与 policy 是两份独立字段，互不影响", () => {
    const p = makePayload({ ...base, model: "child", policy: "review" }, "q1");
    expect(p.model).toBe("child");
    expect(p.policy).toBe("review");
  });
});
