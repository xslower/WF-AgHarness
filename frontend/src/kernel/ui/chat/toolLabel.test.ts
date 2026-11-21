
import { describe, expect, it } from "vitest";
import { coreCommand, toolLabel } from "./toolLabel";

describe("toolLabel 动作名", () => {
  it("文件类工具中文名 + 文件名", () => {
    expect(toolLabel("f_write", { path: "/a/b/report.md" }))
      .toEqual({ title: "写文件", detail: "report.md" });
    expect(toolLabel("f_read", { path: "src/app/main.py" }))
      .toEqual({ title: "读取文件", detail: "main.py" });
  });

  it("f_write 按落点参数显示位置", () => {
    expect(toolLabel("f_write", { path: "a.md", replace: "2,5" }).detail)
      .toBe("a.md · 第 2,5 行");
    expect(toolLabel("f_write", { path: "a.md", before: 3 }).detail)
      .toBe("a.md · 第 3 行前");
    expect(toolLabel("f_write", { path: "a.md", after: 3 }).detail)
      .toBe("a.md · 第 3 行后");
    expect(toolLabel("f_write", { path: "a.md", append: true }).detail)
      .toBe("a.md · 末尾");
  });

  it("f_replace 是独立动作名", () => {
    expect(toolLabel("f_replace", { path: "x/y.md", old: "a", new: "b" }))
      .toEqual({ title: "改文件", detail: "y.md" });
  });

  it("config_write 显示文件名与改动数", () => {
    expect(toolLabel("config_write", {
      path: "config/agent.json",
      ops: [{ op: "set", path: "a", value: 1 }],
    })).toEqual({ title: "写数据文件", detail: "agent.json · 1 处改动" });
    expect(toolLabel("config_write", { path: "a.ini", ops: [] }).detail)
      .toBe("a.ini");
  });

  it("f_path 按 action 细化", () => {
    expect(toolLabel("f_path", { action: "list", path: "/tmp" }).title).toBe("列目录");
    expect(toolLabel("f_path", { action: "delete", path: "a.txt" }).title).toBe("删除");
  });

  it("memory 按 action 显示参数（记忆 vs 翻历史不混）", () => {
    expect(toolLabel("memory", { action: "search", query: "接口前缀" }).detail)
      .toBe("接口前缀");
    expect(toolLabel("memory", { action: "save", content: "约定" }).detail)
      .toBe("约定");
    expect(toolLabel("memory", { action: "replace", mid: "a1b2" }).detail)
      .toBe("a1b2");
    expect(toolLabel("memory", { action: "delete", mid: "a1b2" }).detail)
      .toBe("a1b2");
    expect(toolLabel("memory", { action: "history_get", ids: [3, 7] }).detail)
      .toBe("msg#3,7");
  });

  it("web 区分搜索与打开网页", () => {
    expect(toolLabel("web", { action: "search", query: "rust 教程" }))
      .toEqual({ title: "联网搜索", detail: "rust 教程" });
    expect(toolLabel("web", { action: "fetch", url: "https://x.com" }))
      .toEqual({ title: "打开网页", detail: "https://x.com" });
    expect(toolLabel("web", { action: "inspect", url: "http://localhost:5173" }))
      .toEqual({ title: "调试网页", detail: "http://localhost:5173" });
  });

  it("其余工具都有中文名（不允许漏出英文工具名）", () => {
    const names = ["search_files", "grep", "table", "ppt", "subagent", "memory",
      "workflow", "tool", "todo", "trash", "screenshot", "system_info",
      "gen_image", "asr", "ocr", "run_command"];
    for (const n of names) {
      const { title } = toolLabel(n, {});
      expect(title).not.toBe(n);
      expect(/[a-z_]{4,}/i.test(title)).toBe(false);
    }
  });

  it("MCP 工具显示 server/tool", () => {
    expect(toolLabel("mcp__github__create_issue", {}))
      .toEqual({ title: "github/create_issue", detail: "" });
  });

  it("认不出的工具保留原名、detail 留空", () => {
    expect(toolLabel("some_new_tool", { path: "/a/b" }))
      .toEqual({ title: "some_new_tool", detail: "" });
  });

  it("参数缺失时只给动作名，不报错", () => {
    expect(toolLabel("f_read", undefined)).toEqual({ title: "读取文件", detail: "" });
    expect(toolLabel("f_write", {})).toEqual({ title: "写文件", detail: "" });
    expect(toolLabel("f_replace", {})).toEqual({ title: "改文件", detail: "" });
  });
});

describe("run_command 只显示核心命令", () => {
  it("跳过 cd / timeout / env 这类辅助段", () => {
    expect(coreCommand("cd /tmp && git status")).toBe("git status");
    expect(coreCommand("timeout 30 pytest -x")).toBe("pytest -x");
    expect(coreCommand("env A=1 B=2 python run.py")).toBe("python run.py");
    expect(coreCommand("A=1 npm run build")).toBe("npm run build");
  });

  it("只截命令 + 前两个参数", () => {
    expect(coreCommand("git log --oneline --graph --all -20")).toBe("git log --oneline");
  });

  it("不在白名单的命令只留空（不猜）", () => {
    expect(coreCommand("./deploy.sh --now")).toBe("");
    expect(coreCommand("somebinary -x")).toBe("");
    expect(coreCommand("")).toBe("");
  });

  it("第一条不是命令时继续往后找", () => {
    expect(coreCommand("cd build; make -j4")).toBe("make -j4");
  });
});

describe("toolLabel grep 关键词", () => {
  it("多个 key 展示成一行", () => {
    expect(toolLabel("grep", { key: ["foo", "bar"] }).detail).toBe("foo / bar");
  });
});
