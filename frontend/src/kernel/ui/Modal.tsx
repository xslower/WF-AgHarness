
import type { ReactNode } from "react";

export interface ModalTab<T extends string> {
  id: T;
  label: string;
}

interface Props<T extends string> {
  title?: ReactNode;
  
  tabs?: ModalTab<T>[];
  tab?: T;
  onTab?: (id: T) => void;
  onClose?: () => void;
  
  subtitle?: ReactNode;
  
  flash?: { text: string; err?: boolean } | null;
  
  width?: number;
  children: ReactNode;
}

export function Modal<T extends string>({
  title, tabs, tab, onTab, onClose, subtitle, flash, width, children,
}: Props<T>) {
  return (
    <div className="modal-mask">
      <div className="modal" style={width ? { width } : undefined}>
        <div className="modal-head">
          {tabs?.length ? (
            <div className="tabs">
              {tabs.map((t) => (
                <button key={t.id} className={tab === t.id ? "active" : ""}
                  onClick={() => onTab?.(t.id)}>{t.label}</button>
              ))}
            </div>
          ) : (
            <b className="modal-title">{title}</b>
          )}
          {subtitle && <span className="dim modal-subtitle">{subtitle}</span>}
          {onClose && <button className="link" onClick={onClose}>关闭</button>}
        </div>
        {flash?.text && (
          <div className={`settings-flash ${flash.err ? "err" : "ok"}`}>{flash.text}</div>
        )}
        {children}
      </div>
    </div>
  );
}
