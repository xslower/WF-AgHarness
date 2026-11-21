
import { useEffect } from "react";

import type { EnvEntry } from "../../kernel/api";
import { useEnvs } from "./useEnvs";

export function EnvSection() {
  const c = useEnvs();
  useEffect(() => { void c.reload(); }, []); 
  return (
    <div className="settings-section">
      <h4>运行环境（Python / Node）</h4>
      <p className="dim">禁所有安装。Agent 只能复用这里扫描/绑定的环境；
        命令里的 python/pip/node/npm 会自动改写到绑定路径。</p>
      {c.msg && <div className="notice">{c.msg}</div>}
      <EnvList title="Python 环境" items={c.pythonEnvs} bound={c.bindings.python}
        onBind={(p) => void c.bind("python", p)} />
      <EnvList title="Node 环境" items={c.nodeEnvs} bound={c.bindings.node}
        onBind={(p) => void c.bind("node", p)} />
      <div className="row">
        <button onClick={() => void c.reload()}>↻ 重新扫描</button>
      </div>
      <div className="row">
        <input value={c.newPath} placeholder="新建 venv 路径（仅人工触发，如 D:/envs/proj-venv）"
          onChange={(e) => c.setNewPath(e.target.value)} />
        <button onClick={() => void c.createVenv()}>新建 venv</button>
      </div>
    </div>
  );
}

function EnvList({ title, items, bound, onBind }: {
  title: string; items: EnvEntry[]; bound: string; onBind: (path: string) => void;
}) {
  return (
    <>
      <h5>{title}（{items.length}）</h5>
      {items.map((e) => (
        <div key={e.path} className="queue-item">
          <span>{e.name}<br /><span className="dim">{e.path}</span></span>
          <button className={`link ${bound === e.path ? "ok-badge" : ""}`}
            onClick={() => onBind(e.path)}>
            {bound === e.path ? "✓ 已绑定" : "绑定"}
          </button>
        </div>
      ))}
    </>
  );
}
