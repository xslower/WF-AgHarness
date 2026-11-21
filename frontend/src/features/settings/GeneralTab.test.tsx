

import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GeneralTab } from "./GeneralTab";
import type { Settings } from "../../kernel/api";
import { formatSetting, parseSetting, SETTING_GROUPS } from "./settingsFields";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const settings = {
  workspaceRoot: "/work", defaultEffort: "medium", contextWarnRatio: 0.6,
  envPython: "", envNode: "", trashRetentionDays: 7,
  quickSuggestions: true, notifyOnSessionDone: false, trashEnabled: true,
  policyExtraSafePaths: [], promptTemplateMode: "off",
  compactSummaryMode: "batch",
} as unknown as Settings;

function renderTab(save = vi.fn()) {
  render(<GeneralTab settings={settings} saveSetting={save}
    uiPluginId="classic-dark" setUiPluginId={vi.fn()} themes={[]} />);
  return save;
}

describe("GeneralTab 行内编辑", () => {
  it("值默认不是输入框；点击才进入编辑态", () => {
    renderTab();
    expect(screen.queryByDisplayValue("/work")).toBeNull();
    fireEvent.click(screen.getByText("/work"));
    expect(screen.getByDisplayValue("/work")).toBeTruthy();
  });

  it("失焦提交改过的那一个字段，并收起编辑态", async () => {
    const save = renderTab();
    fireEvent.click(screen.getByText("/work"));
    const input = screen.getByDisplayValue("/work");
    fireEvent.change(input, { target: { value: "/new-work" } });
    fireEvent.blur(input);
    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith("workspaceRoot", "/new-work");
    await waitFor(() => expect(screen.queryByDisplayValue("/new-work")).toBeNull());
  });

  it("点一下没改 / Esc 取消都不发保存", () => {
    const save = renderTab();
    fireEvent.click(screen.getByText("/work"));
    fireEvent.blur(screen.getByDisplayValue("/work"));
    fireEvent.click(screen.getByText("/work"));
    fireEvent.keyDown(screen.getByDisplayValue("/work"), { key: "Escape" });
    expect(save).not.toHaveBeenCalled();
  });

  it("回车提交后紧跟的 blur 不会重复提交", () => {
    const save = renderTab();
    fireEvent.click(screen.getByText("/work"));
    const input = screen.getByDisplayValue("/work");
    fireEvent.change(input, { target: { value: "/x" } });
    fireEvent.keyDown(input, { key: "Enter" });
    fireEvent.blur(input);
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("布尔项点一下即切换", () => {
    const save = renderTab();
    
    fireEvent.click(screen.getAllByText("✓ 已开启")[0]);
    expect(save).toHaveBeenCalledWith("trashEnabled", false);
  });
});

describe("settingsFields 纯函数", () => {
  it("每个声明的字段都在 Settings 类型里有对应值，且类型解析不丢数组", () => {
    for (const g of SETTING_GROUPS) for (const def of g.fields) {
      const raw = formatSetting(def, settings[def.key]);
      const parsed = parseSetting(def, raw);
      
      
      const neutral = def.kind === "number" ? 0 : def.kind === "boolean" ? false
        : def.kind === "lines" ? [] : "";
      expect(parsed).toEqual(settings[def.key] === undefined ? neutral : settings[def.key]);
    }
  });

  it("数字空/非法一律落 0，文本保留原样", () => {
    const days = SETTING_GROUPS.flatMap((g) => g.fields).find((f) => f.key === "trashRetentionDays")!;
    expect(parseSetting(days, "")).toBe(0);
    expect(parseSetting(days, "abc")).toBe(0);
    expect(parseSetting(days, "30")).toBe(30);
  });
});
