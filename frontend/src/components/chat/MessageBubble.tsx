import { emotionByLabel, EMOTION_KEYS, EMOTION_THEME } from '../../theme/emotion';
import { AI_EMOJI, AI_NAME } from '../../theme/companion';
import { formatTime } from '../../utils/format';

/** 情绪强度文字化（让"被看见"更具体）。 */
function intensityText(v?: number | null): string | null {
  if (v == null) return null;
  if (v >= 0.7) return '· 情绪很强';
  if (v >= 0.4) return '· 有些明显';
  return '· 轻微';
}

/** 兜底剥离历史消息中残留的【情绪标签：xxx】标记。 */
const TAG_RE = /[【\[]\s*(?:情绪标签|情绪)\s*[:：]?\s*[^】\]\n]{0,12}[】\]]/g;
function stripTag(text: string): string {
  return text.replace(TAG_RE, '').trim();
}

/** 消息气泡：用户靠右（蓝），AI 靠左（情绪主题色）。 */
export default function MessageBubble({
  role,
  content,
  emotionLabel,
  emotionIntensity,
  isPrivate,
  isQuickCheckin,
  time,
}: {
  role: string;
  content: string;
  emotionLabel?: string | null;
  emotionIntensity?: number | null;
  isPrivate?: boolean;
  isQuickCheckin?: boolean;
  time?: string;
}) {
  const theme = emotionByLabel(emotionLabel);

  if (role === 'user') {
    return (
      <div className="msg-row user fade-up">
        <div className="msg">
          {isQuickCheckin && <span className="checkin-tag">情绪打卡</span>}
          {isPrivate && <span className="privacy-tag">仅本次会话</span>}
          {stripTag(content)}
          {time && <div className="msg-time">{formatTime(time)}</div>}
        </div>
        <div className="msg-avatar user">🙂</div>
      </div>
    );
  }

  return (
    <div className="msg-row ai fade-up">
      <div className="msg-avatar ai">{AI_EMOJI}</div>
      <div
        className="msg"
        style={{ borderColor: theme.color }}
      >
        <div className="ai-bar" style={{ background: theme.color }} />
        {isPrivate && <span className="privacy-tag">仅本次会话</span>}
        <div className="ai-meta">
          <span className="ai-name">{AI_NAME}</span>
          {time && <span className="msg-time">{formatTime(time)}</span>}
        </div>
        <div className="ai-content">{stripTag(content)}</div>
        {emotionLabel && (
          <div className="ai-emotion" style={{ color: theme.color }}>
            {theme.emoji} 感知到你的情绪：{theme.label}
            {intensityText(emotionIntensity) && (
              <span className="ai-emotion-sub">{intensityText(emotionIntensity)}</span>
            )}
          </div>
        )}
        {emotionLabel === '低落' && (
          <div className="ai-pat">轻轻拍了拍你 🫂</div>
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
