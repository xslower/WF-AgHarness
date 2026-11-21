
import { useEffect, useState } from "react";

import type { McpServerCfg } from "../../kernel/api";
import { useMcpServers } from "./useMcpServers";


function toLines(obj: Record<string, string> | undefined): string {
  return Object.entries(obj || {}).map(([k, v]) => `${k}=${v}`).join("\n");
}

function fromLines(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const i = line.indexOf("=");
    if (i <= 0) continue;
    const k = line.slice(0, i).trim();
    if (k) out[k] = line.slice(i + 1).trim();
  }
  return out;
}

function ServerCard({
  name, cfg, st, c,
}: {
  name: string;
  cfg: McpServerCfg;
  st?: { connected: boolean; tools: string[]; error?: string; error_detail?: string;
         disabled?: boolean; disabled_reason?: string };
  c: ReturnType<typeof useMcpServers>;
}) {
  const [open, setOpen] = useState(false);
  const transport = cfg.transport || "stdio";
  return (
    <div className="provider-card">
      <div className="row" style={{ alignItems: "center", gap: 8 }}>
        <strong>{name}</strong>
        {cfg.desc && <span className="dim" style={{ fontSize: 12 }}>{cfg.desc}</span>}
        <span style={{ flex: 1 }} />
        {st?.disabled
          ? <span className="err-badge" title={st.disabled_reason}>
              ⊘ 已禁用{st.disabled_reason ? `（${st.disabled_reason}）` : ""}
            </span>
          : st && (st.connected
            ? <span className="ok-badge">✓ 已连接 · {st.tools.length} 工具</span>
            : <span className="err-badge" title={st.error || "原因未知"}>
                ✗ 未连接{st.error ? `（${st.error}）` : ""}
              </span>)}
        <button onClick={() => void c.reconnect(name)}>重连</button>
        <button onClick={() => setOpen((v) => !v)}>{open ? "收起" : "编辑"}</button>
        <button className="danger" onClick={() => void c.removeServer(name)}>删除</button>
      </div>

      {st && !st.connected && st.error_detail && open && (
        <details>
          <summary className="dim" style={{ fontSize: 12 }}>详细错误</summary>
          <pre className="dim" style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>{st.error_detail}</pre>
        </details>
      )}

      {open && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
          <div className="row" style={{ gap: 6 }}>
            <span className="dim" style={{ width: 76 }}>传输</span>
            <select value={transport}
              onChange={(e) => c.patch(name, { transport: e.target.value })}>
              <option value="stdio">stdio（本地进程）</option>
              <option value="sse">sse（HTTP 长连接）</option>
              <option value="http">http（Streamable HTTP）</option>
            </select>
            <label className="row" style={{ gap: 4, marginLeft: 12 }}>
              <input type="checkbox" checked={Boolean(cfg.enabled ?? true)}
                onChange={(e) => c.patch(name, { enabled: e.target.checked })} />
              启用
            </label>
            <label className="row" style={{ gap: 4 }}>
              <input type="checkbox" checked={Boolean(cfg.lazy)}
                onChange={(e) => c.patch(name, { lazy: e.target.checked })} />
              懒连接
            </label>
          </div>

          <div className="row" style={{ gap: 6 }}>
            <span className="dim" style={{ width: 76 }}>说明</span>
            <input value={cfg.desc || ""} placeholder="一句话说明（可选）"
              style={{ flex: 1 }}
              onChange={(e) => c.patch(name, { desc: e.target.value })} />
          </div>

          {transport === "stdio" ? (
            <>
              <div className="row" style={{ gap: 6 }}>
                <span className="dim" style={{ width: 76 }}>命令</span>
                <input value={cfg.command} placeholder="如 npx / python / uvx"
                  style={{ flex: 1 }}
                  onChange={(e) => c.patch(name, { command: e.target.value })} />
              </div>
              <div className="row" style={{ gap: 6 }}>
                <span className="dim" style={{ width: 76 }}>参数</span>
                <input value={cfg.args.join(" ")} placeholder="空格分隔"
                  style={{ flex: 1 }}
                  onChange={(e) => c.patch(name, {
                    args: e.target.value.split(/\s+/).filter(Boolean),
                  })} />
              </div>
            </>
          ) : (
            <div className="row" style={{ gap: 6 }}>
              <span className="dim" style={{ width: 76 }}>端点</span>
              <input value={cfg.url || ""} placeholder="https://host/sse"
                style={{ flex: 1 }}
                onChange={(e) => c.patch(name, { url: e.target.value })} />
            </div>
          )}

          <div className="row" style={{ gap: 6, alignItems: "flex-start" }}>
            <span className="dim" style={{ width: 76 }}>环境变量</span>
            <textarea rows={3} style={{ flex: 1, fontFamily: "monospace", fontSize: 12 }}
              placeholder={"KEY=value（每行一条，${VAR} 表示读环境变量）"}
              value={toLines(cfg.env)}
              onChange={(e) => c.patch(name, { env: fromLines(e.target.value) })} />
          </div>

          {transport !== "stdio" && (
            <div className="row" style={{ gap: 6, alignItems: "flex-start" }}>
              <span className="dim" style={{ width: 76 }}>请求头</span>
              <textarea rows={2} style={{ flex: 1, fontFamily: "monospace", fontSize: 12 }}
                placeholder={"Authorization=Bearer xxx（每行一条）"}
                value={toLines(cfg.headers)}
                onChange={(e) => c.patch(name, { headers: fromLines(e.target.value) })} />
            </div>
          )}

          <div className="row">
            <button className="primary" onClick={() => void c.save(name)}>保存并重连</button>
          </div>
        </div>
      )}
    </div>
  );
}

export function McpTab() {
  const c = useMcpServers();

  useEffect(() => { void c.reload(); }, []); 

  return (
    <div className="panel">
      <div className="provider-card">
        <div className="row" style={{ alignItems: "center", gap: 8 }}>
          <strong>GitHub Token</strong>
          {c.github.configured
            ? <span className="ok-badge">✓ 已配置 {c.github.hint}</span>
            : <span className="err-badge">✗ 未配置</span>}
          <span className="dim" style={{ fontSize: 12 }}>
            {c.github.source ? `来源：${c.github.source}` : ""}
          </span>
        </div>
        <p className="dim" style={{ fontSize: 12, margin: "4px 0" }}>
          <b>skill 探索与 github MCP 服务器都依赖这个 token</b>（加密存储）。
          未配置时 skill 探索会降级为仓库搜索、github MCP 的 search_code 会认证失败。
        </p>
        <div className="row" style={{ gap: 6 }}>
          <input type="password" value={c.tokenDraft}
            placeholder={c.github.configured ? "留空=不修改" : "github_pat_..."}
            style={{ flex: 1 }}
            onChange={(e) => c.setTokenDraft(e.target.value)} />
          <button onClick={() => void c.saveToken()}>保存</button>
          <button onClick={() => void c.testToken()}>测试连接</button>
        </div>
      </div>

      <p className="dim" style={{ fontSize: 12 }}>
        每个服务器是一个 json 文件（<code>data/mcp/&lt;名字&gt;.json</code>），
        改完点「保存并重连」立即生效。工具以 <code>mcp__服务器__工具</code> 形式注入。
      </p>
      {c.msg && <div className="notice">{c.msg}</div>}

      {Object.entries(c.servers).map(([name, cfg]) => (
        <ServerCard key={name} name={name} cfg={cfg}
          st={c.status.find((s) => s.name === name)} c={c} />
      ))}

      <div className="row">
        <input value={c.newName} placeholder="新服务器名称"
          onChange={(e) => c.setNewName(e.target.value)} />
        <button onClick={() => void c.addServer()}>+ 添加</button>
      </div>
    </div>
  );
}
