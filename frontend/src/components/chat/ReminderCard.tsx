import { AI_NAME, REMINDER_DONE_REPLY } from '../../theme/companion';

/**
 * 可打卡的贴心提醒卡片（受控组件：done 状态由父组件管理）。
 * 打卡完成后卡片留在消息流历史中，不再跟随底部。
 * 支持自定义标题（如「小光 · WorkBuddy」）。
 */
export default function ReminderCard({
  icon,
  text,
  title = '小光 · 贴心提醒',
  done,
  onCheck,
}: {
  icon: string;
  text: string;
  title?: string;
  done: boolean;
  onCheck: () => void;
}) {
  return (
    <div className={`reminder-card${done ? ' done' : ''}`}>
      <div className="reminder-icon">{icon}</div>
      <div className="reminder-body">
        <div className="reminder-title">{title}</div>
        <div className="reminder-text">{text}</div>
        {done ? (
          <div className="reminder-done">✓ {REMINDER_DONE_REPLY}</div>
        ) : (
          <button className="btn btn-ghost reminder-check" onClick={onCheck}>
            ✓ 完成打卡
          </button>
        )}
      </div>
    </div>
  );
}

