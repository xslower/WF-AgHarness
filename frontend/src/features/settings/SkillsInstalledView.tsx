
import type { SkillsController } from "./useSkills";

export function InstalledView({ s }: { s: SkillsController }) {
  return (
    <>
      <div className="q-title">从 URL 安装</div>
      <div className="dim pad8">
        粘贴 SKILL.md 直链地址（GitHub raw 等），或切换到「探索发现」浏览后一键安装。
      </div>
      <div className="row" style={{ gap: 8, padding: "8px 0", flexWrap: "wrap" }}>
        <input type="text" placeholder="SKILL.md 直链 URL" value={s.url}
          onChange={(e) => s.setUrl(e.target.value)}
          style={{ flex: 1, minWidth: 260 }} />
        <input type="text" placeholder="自定义名称（可选）" value={s.custName}
          onChange={(e) => s.setCustName(e.target.value)}
          style={{ width: 140 }} />
        <button onClick={() => void s.installFromUrl()} disabled={s.busy || !s.url.trim()}>
          {s.busy ? "..." : "安装"}
        </button>
      </div>

      {s.skills.length === 0 && (
        <div className="dim pad8">暂无已安装的 Skill。切换到「探索发现」浏览远程仓库。</div>
      )}

      {s.skills.map((k) => (
        <div key={k.name} className="provider-card">
          <div className="row" style={{ alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <b>{k.display || k.name}</b>
            {k.source && k.source !== "builtin" && (
              <span className="projhome-badge">{k.source === "project" ? "项目" : "插件"}</span>
            )}
            <span className="dim">{k.lines} 行</span>
            {k.tags.map((t) => (
              <span key={t} className="dim"
                style={{ background: "var(--bg2)", padding: "1px 6px", borderRadius: 3, fontSize: 11 }}>
                {t}
              </span>
            ))}
            <span style={{ flex: 1 }} />
            <button className="link" onClick={() => void s.remove(k.name)} disabled={s.busy}
              style={{ color: "var(--err)", fontSize: 12 }}>删除</button>
          </div>
          {k.desc && <div className="dim" style={{ marginTop: 4 }}>{k.desc}</div>}
        </div>
      ))}
    </>
  );
}
