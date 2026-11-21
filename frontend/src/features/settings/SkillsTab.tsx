
import { useEffect } from "react";

import { ExploreView } from "./SkillsExploreView";
import { InstalledView } from "./SkillsInstalledView";
import { useSkills } from "./useSkills";

export function SkillsTab() {
  const s = useSkills();

  useEffect(() => { void s.loadInstalled(); }, []); 

  return (
    <div className="tab-content">
      <div className="row" style={{ gap: 8, marginBottom: 12 }}>
        <button className={s.view === "installed" ? "active" : ""}
          onClick={() => s.setView("installed")}>
          已安装 ({s.skills.length})
        </button>
        <button className={s.view === "explore" ? "active" : ""}
          onClick={() => s.setView("explore")}>
          探索发现
        </button>
      </div>

      {s.view === "installed" ? <InstalledView s={s} /> : <ExploreView s={s} />}

      {s.msg && (
        <div className="dim pad8" style={{ color: s.msg.startsWith("✗") ? "var(--err)" : undefined }}>
          {s.msg}
        </div>
      )}
    </div>
  );
}
