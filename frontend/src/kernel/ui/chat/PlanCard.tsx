import React, { useRef, useState } from 'react';
import type { PlanState } from './useChatStream';
import { Icon } from "../icons";

interface PlanCardProps {
  planState: PlanState;
  onApprove: () => void;
  
  onModify: (feedback: string) => void;
  
  onEditFull: (planText: string) => void;
  onCancel: () => void;
  busy: boolean;
}


const PlanCard: React.FC<PlanCardProps> = ({
  planState,
  onApprove,
  onModify,
  onEditFull,
  onCancel,
  busy,
}) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  
  
  
  const submitted = useRef(false);
  if (planState.status !== 'awaiting_approval') return null;

  const guard = (fn: () => void) => () => {
    if (submitted.current || busy) return;
    submitted.current = true;
    fn();
  };

  const submitFeedback = () => {
    const fb = feedback.trim();
    if (!fb || submitted.current || busy) return;
    submitted.current = true;
    setShowFeedback(false);
    setFeedback('');
    onModify(fb);
  };

  return (
    <div className="float-plan">
      <div className="float-plan-head">
        <Icon name="plan" />
        <b>实施计划已生成，请确认</b>
      </div>
      <div className="float-actions">
        <button className="primary" onClick={guard(onApprove)} disabled={busy}>
          <Icon name="check" /> 确认执行
        </button>
        <button onClick={() => setShowFeedback((v) => !v)} disabled={busy}>
          <Icon name="pencil" /> 提修改意见
        </button>
        <button onClick={guard(() => onEditFull(planState.planText))} disabled={busy}>
          <Icon name="file-text" /> 编辑全文
        </button>
        <button onClick={guard(onCancel)} disabled={busy}>
          <Icon name="x" /> 取消
        </button>
      </div>

      {showFeedback && (
        <div className="plan-fb">
          <textarea
            autoFocus
            rows={3}
            value={feedback}
            placeholder="说明要改哪几步，例如：第 2 步不要动 .env，改成先备份再覆盖"
            onChange={(e) => setFeedback(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submitFeedback();
            }}
          />
          <div className="float-actions">
            <button className="primary" onClick={submitFeedback}
              disabled={busy || !feedback.trim()}>
              提交意见，重新生成计划
            </button>
            <button onClick={() => { setShowFeedback(false); setFeedback(''); }}>收起</button>
          </div>
        </div>
      )}

      <div className="float-hint">
        提意见 = 让模型在原计划上改；编辑全文 = 填进输入框由你直接改，发送后按定稿执行、不再重写
      </div>
    </div>
  );
};

export default PlanCard;
