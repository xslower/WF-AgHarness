
import { useState } from "react";

import { Icon } from "../../kernel/ui/icons";
import type { TimerJob } from "../../kernel/api/types";
import {
  emptyTimerDraft, toDraft, useProjectTimers, type TimerDraft,
} from "./useProjectTimers";


function fmtNext(ts: number | null): string {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}


function fmtSpec(job: TimerJob): string {
  if (job.kind === "cron") return `cron ${job.spec}`;
  const sec = Number(job.spec);
  if (!Number.isFinite(sec)) return job.spec;
  if (sec % 3600 === 0) return `每 ${sec / 3600} 小时`;
  if (sec % 60 === 0) return `每 ${sec / 60} 分钟`;
  return `每 ${sec} 秒`;
}

export function ProjectTimers(props: { project: string }) {
  const c = useProjectTimers(props.project);
  
  const [editing, setEditing] = useState<{ job: TimerJob | null } | null>(null);

  return (
    <section className="projhome-sec">
      <h3>
        定时任务 <em>{c.jobs.length}</em>
        <button className="icon-btn" title="新建定时任务"
          onClick={() => setEditing({ job: null })}>
          <Icon name="plus" />
        </button>
      </h3>
      <div className="projhome-hint">
        <b>后端</b>到点在后端进程里直接跑，页面关着也生效；
        <b>前端</b>到点用当前浏览器跑（效果同「开了会话然后切走」），关掉页面就停。
        未启用时到点不会触发。
      </div>
      {c.error && <div className="projhome-err-inline">{c.error}</div>}
      {c.jobs.length === 0 ? (
        <div className="projhome-empty">还没有定时任务</div>
      ) : (
        <div className="projhome-list">
          {c.jobs.map((j) => (
            <div key={j.name} className="projhome-row static">
              <span className="projhome-row-title">
                {j.name}
                <span className="projhome-badge">{j.owner === "backend" ? "后端" : "前端"}</span>
                <span className="projhome-badge">
                  {j.action === "session" ? "会话" : "工作流"}
                </span>
                {!j.enabled && <span className="projhome-badge">已停用</span>}
              </span>
              <span className="projhome-row-meta">
                <span className="projhome-row-text">
                  {fmtSpec(j)} · 下次 {fmtNext(j.nextRunAt)}
                  {j.invalid ? "（表达式非法）" : ""}
                </span>
                <button disabled={c.busy === j.name}
                  onClick={() => void c.toggle(j)}>
                  {j.enabled ? "停用" : "启用"}
                </button>
                <button disabled={c.busy === j.name}
                  onClick={() => setEditing({ job: j })}>编辑</button>
                <button className="icon-btn projhome-del" title="删除定时任务"
                  disabled={c.busy === j.name}
                  onClick={() => void c.remove(j.name)}><Icon name="trash" /></button>
              </span>
            </div>
          ))}
        </div>
      )}
      {editing && (
        <TimerDialog
          project={props.project}
          job={editing.job}
          onCreate={c.create}
          onSave={c.save}
          onClose={() => setEditing(null)} />
      )}
    </section>
  );
}


function TimerDialog(props: {
  project: string;
  job: TimerJob | null;
  onCreate: (d: TimerDraft) => Promise<void>;
  onSave: (job: TimerJob, d: TimerDraft) => Promise<void>;
  onClose: () => void;
}) {
  const [d, setD] = useState<TimerDraft>(
    props.job ? toDraft(props.job) : { ...emptyTimerDraft, target: props.project });
  const set = <K extends keyof TimerDraft>(k: K, v: TimerDraft[K]) =>
    setD((old) => ({ ...old, [k]: v }));
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    try {
      if (props.job) await props.onSave(props.job, d);
      else await props.onCreate(d);
      props.onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="projhome-uiprefs" style={{ marginTop: 8 }}>
      <div className="projhome-hint">
        {props.job ? `编辑：${props.job.name}` : "新建定时任务"}
      </div>
      <label className="projhome-switch">名称
        <input value={d.name} disabled={!!props.job}
          placeholder="例：daily-report（不能带 . / *）"
          onChange={(e) => set("name", e.target.value)} />
      </label>
      <label className="projhome-switch">在哪跑
        <select value={d.owner}
          onChange={(e) => set("owner", e.target.value as TimerDraft["owner"])}>
          <option value="frontend">前端（浏览器，关页面就停）</option>
          <option value="backend">后端（进程内，人不在也跑）</option>
        </select>
      </label>
      <label className="projhome-switch">类型
        <select value={d.action}
          onChange={(e) => set("action", e.target.value as TimerDraft["action"])}>
          <option value="session">定时会话</option>
          <option value="workflow">定时工作流</option>
        </select>
      </label>
      <label className="projhome-switch">频率
        <select value={d.kind}
          onChange={(e) => set("kind", e.target.value as TimerDraft["kind"])}>
          <option value="every">固定间隔（秒）</option>
          <option value="cron">cron 表达式</option>
        </select>
        <input value={d.spec} onChange={(e) => set("spec", e.target.value)}
          placeholder={d.kind === "every" ? "3600" : "0 9 * * mon"} />
      </label>
      <div className="projhome-hint">
        cron 是 5 段（分 时 日 月 周），<b>星期写 mon..sun</b>（0 = 周一，不是周日）。
      </div>
      {d.action === "session" ? (
        <label className="projhome-switch">提示词
          <textarea rows={4} value={d.prompt} onChange={(e) => set("prompt", e.target.value)}
            placeholder="到点后用这段提示词新建一条会话请求 LLM" />
        </label>
      ) : (
        <label className="projhome-switch">工作流名
          <input value={d.workflow} onChange={(e) => set("workflow", e.target.value)}
            placeholder="本项目或全局的工作流名" />
        </label>
      )}
      <div>
        <button disabled={saving} onClick={() => void submit()}>
          {saving ? "保存中…" : "保存"}
        </button>
        <button onClick={props.onClose}>取消</button>
      </div>
    </div>
  );
}
