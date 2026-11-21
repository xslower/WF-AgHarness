
import type { SkillsController } from "./useSkills";

export function ExploreView({ s }: { s: SkillsController }) {
  return (
    <>
      <div className="row" style={{ gap: 8, padding: "8px 0", flexWrap: "wrap" }}>
        <input type="text" placeholder="搜索关键词（如 openclaw、claude、obsidian）"
          value={s.query} onChange={(e) => s.setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void s.explore(1)}
          style={{ flex: 1, minWidth: 220 }} />
        <button onClick={() => void s.explore(1)} disabled={s.busy}>
          {s.busy ? "搜索中..." : "搜索"}
        </button>
      </div>

      {s.degraded.on && (
        <div className="notice" style={{ marginBottom: 8 }}>
          {s.degraded.note || "搜索精度受限"}
        </div>
      )}

      {s.exploreTotal > 0 && (
        <div className="dim pad8">共 {s.exploreTotal} 个结果，第 {s.page} 页</div>
      )}

      {s.exploreItems.length === 0 && !s.busy && (
        <div className="dim pad8">输入关键词搜索 GitHub 上包含 SKILL.md 的仓库。</div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 8 }}>
        {s.exploreItems.map((item) => (
          <div key={item.fullName} className="provider-card"
            style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div className="row" style={{ alignItems: "center", gap: 6 }}>
              <b style={{ fontSize: 13 }}>{item.fullName}</b>
              <span className="dim" style={{ fontSize: 11 }}>⭐ {item.stars.toLocaleString()}</span>
            </div>
            {item.description && (
              <div className="dim" style={{ fontSize: 12, lineHeight: 1.4, flex: 1 }}>
                {item.description.length > 120 ? item.description.slice(0, 120) + "..." : item.description}
              </div>
            )}
            <div className="row" style={{ gap: 4, flexWrap: "wrap", marginTop: 4 }}>
              {item.topics.slice(0, 5).map((t) => (
                <span key={t} className="dim"
                  style={{ background: "var(--bg2)", padding: "1px 5px", borderRadius: 3, fontSize: 10 }}>
                  {t}
                </span>
              ))}
            </div>
            <div className="row" style={{ gap: 6, marginTop: 4 }}>
              <button onClick={() => void s.installFromExplore(item)}
                disabled={s.installing === item.fullName}
                style={{ fontSize: 12, padding: "2px 10px" }}>
                {s.installing === item.fullName ? "安装中..." : "安装"}
              </button>
              <a href={item.url} target="_blank" rel="noopener" className="link" style={{ fontSize: 11 }}>
                GitHub
              </a>
            </div>
          </div>
        ))}
      </div>

      {s.exploreItems.length > 0 && (
        <div className="row" style={{ justifyContent: "center", gap: 8, padding: "12px 0" }}>
          <button onClick={() => void s.explore(s.page - 1)} disabled={s.page <= 1 || s.busy}>
            ← 上一页
          </button>
          <span className="dim">{s.page}</span>
          <button onClick={() => void s.explore(s.page + 1)} disabled={!s.hasMore || s.busy}>
            下一页 →
          </button>
        </div>
      )}
    </>
  );
}
