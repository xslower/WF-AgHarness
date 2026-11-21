
import type { Checkpoint } from "../../kernel/api";
import { alertDialog } from "../../kernel/ui/dialog";
import { fmtStamp } from "../../kernel/ui/format";
import { useSnapshots } from "./useSnapshots";

interface Props {
  project: string;
  showSnaps: boolean;
  setShowSnaps: (v: boolean) => void;
  cks: Checkpoint[];
  setCks: (v: Checkpoint[]) => void;
}

export function SnapshotPanel({ project, showSnaps, setShowSnaps, cks, setCks }: Props) {
  const snaps = useSnapshots(project, setCks, (msg) => void alertDialog(msg));

  return (
    <div className="art-snaps">
      <div className="q-title link" onClick={() => setShowSnaps(!showSnaps)}>
        {showSnaps ? "▾" : "▸"} 快照 / 回滚
      </div>
      {showSnaps && (
        <>
          <button onClick={() => void snaps.create()}>＋ 创建快照</button>
          {cks.map((c) => (
            <div key={c.sha} className="art-item">
              <span className="art-name">
                {fmtStamp(c.ts)} · {c.message}
              </span>
              <button className="link del" onClick={() => void snaps.restore(c)}>回滚</button>
            </div>
          ))}
          {!cks.length && <div className="dim">暂无快照（Agent 改文件前会自动快照）</div>}
        </>
      )}
    </div>
  );
}
