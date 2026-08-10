import { useState } from 'react';

/** 快捷时间建议。 */
const QUICK_TIMES = ['18:00', '19:00', '20:00', '21:00', '22:00'];

/** 默认时间：取传入 dueAt 的时分。 */
function defaultTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

interface Props {
  /** 小光提示文案（"想几点开始呀？"）。 */
  text: string;
  /** 计划暂定时间（取日期部分用于最终确认）。 */
  dueAt: string;
  /** 是否已确认（由父级切换）。 */
  confirmed: boolean;
  onConfirm: (timeStr: string) => void;
  onDismiss: () => void;
}

/** 对话里识别到"没有明确几点"的计划时，小光反问并让用户一键定时间。 */
export default function ScheduleTimeConfirm({ text, dueAt, confirmed, onConfirm, onDismiss }: Props) {
  const [time, setTime] = useState(() => defaultTime(dueAt));
  const [finalTime, setFinalTime] = useState<string | null>(null);

  if (confirmed && finalTime) {
    return <div className="ai-content sched-confirm-ok">✅ 已定好 {finalTime}，到点提醒你 ⏰</div>;
  }

  return (
    <div className="ai-content sched-confirm">
      <div>{text}</div>
      <div className="sched-confirm-pick">
        {QUICK_TIMES.map((t) => (
          <button
            key={t}
            className={`sched-time-chip${time === t ? ' active' : ''}`}
            onClick={() => setTime(t)}
          >
            {t}
          </button>
        ))}
        <input
          className="input sched-confirm-input"
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
        />
      </div>
      <div className="sched-confirm-actions">
        <button
          className="btn btn-sm"
          onClick={() => {
            setFinalTime(time);
            onConfirm(time);
          }}
        >
          确定，到点提醒我
        </button>
        <button className="btn btn-ghost btn-sm" onClick={onDismiss}>
          先不设
        </button>
      </div>
    </div>
  );
}
