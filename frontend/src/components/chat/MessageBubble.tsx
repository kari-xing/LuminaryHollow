import { emotionByLabel, EMOTION_KEYS, EMOTION_THEME } from '../../theme/emotion';

/** 情绪强度文字化（让"被看见"更具体）。 */
function intensityText(v?: number | null): string | null {
  if (v == null) return null;
  if (v >= 0.7) return '· 情绪很强';
  if (v >= 0.4) return '· 有些明显';
  return '· 轻微';
}

/** 消息气泡：用户靠右（蓝），AI 靠左（情绪主题色）。 */
export default function MessageBubble({
  role,
  content,
  emotionLabel,
  emotionIntensity,
  isPrivate,
  isQuickCheckin,
}: {
  role: string;
  content: string;
  emotionLabel?: string | null;
  emotionIntensity?: number | null;
  isPrivate?: boolean;
  isQuickCheckin?: boolean;
}) {
  const theme = emotionByLabel(emotionLabel);

  if (role === 'user') {
    return (
      <div className="msg-row user">
        <div className="msg user-msg fade-up">
          {isQuickCheckin && <span className="checkin-tag">情绪打卡</span>}
          {isPrivate && <span className="privacy-tag">仅本次会话</span>}
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="msg-row ai">
      <div
        className="msg ai-msg fade-up"
        style={{ borderColor: theme.color, background: theme.soft }}
      >
        <div className="ai-bar" style={{ background: theme.color }} />
        {isPrivate && <span className="privacy-tag">仅本次会话</span>}
        <div className="ai-content">{content}</div>
        {emotionLabel && (
          <div className="ai-emotion" style={{ color: theme.color }}>
            {theme.emoji} 感知到你的情绪：{theme.label}
            {intensityText(emotionIntensity) && (
              <span className="ai-emotion-sub">{intensityText(emotionIntensity)}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** 输入框上方快捷情绪记录图标组。 */
export function QuickEmotionPicker({ onPick }: { onPick: (label: string) => void }) {
  return (
    <div className="quick-picker">
      {EMOTION_KEYS.map((k) => (
        <button
          key={k}
          className="quick-btn"
          title={`记录：${EMOTION_THEME[k].label}`}
          onClick={() => onPick(EMOTION_THEME[k].label)}
        >
          {EMOTION_THEME[k].emoji}
        </button>
      ))}
      <span className="quick-hint">点一下，记录此刻心情</span>
    </div>
  );
}
