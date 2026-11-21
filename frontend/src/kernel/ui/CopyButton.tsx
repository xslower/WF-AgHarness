
import { useEffect, useRef, useState, type ReactNode } from "react";
import { clipboardPermission, clipboardState, copyText } from "./clipboard";

export function CopyButton({
  text, className = "link", label = "复制", children = "⧉",
}: {
  text: string;
  className?: string;
  label?: string;
  children?: ReactNode;
}) {
  const [copied, setCopied] = useState(false);
  const [hint, setHint] = useState("");
  const [perm, setPerm] = useState("");
  const copiedTimer = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    void clipboardPermission().then((p) => { if (alive) setPerm(p); });
    return () => {
      alive = false;
      if (copiedTimer.current !== null) window.clearTimeout(copiedTimer.current);
    };
  }, []);

  const insecure = clipboardState() === "insecure";
  const ask = insecure
    ? "当前页面无法申请剪贴板权限（需 https 或 localhost）；点此查看解决办法"
    : perm === "denied"
      ? "剪贴板权限已被拒绝；点此重试并查看恢复步骤"
      : `${label}（点击时浏览器会申请剪贴板权限）`;

  const onClick = async () => {
    setHint("");
    const r = await copyText(text);
    if (!r.ok) {
      setCopied(false);
      setHint(r.hint);
      return;
    }
    setCopied(true);
    if (copiedTimer.current !== null) window.clearTimeout(copiedTimer.current);
    copiedTimer.current = window.setTimeout(() => {
      setCopied(false);
      copiedTimer.current = null;
    }, 1500);
  };

  return (
    <span className="copy-wrap">
      <button type="button" className={className} title={ask} aria-label={label}
        onClick={(e) => { e.stopPropagation(); void onClick(); }}>
        {copied ? "✓" : children}
      </button>
      {hint && (
        <span className="copy-hint" role="alert" title="点此关闭"
          onClick={() => setHint("")}>{hint} <b>×</b></span>
      )}
    </span>
  );
}
