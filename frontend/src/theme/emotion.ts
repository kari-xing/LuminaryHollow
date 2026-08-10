/** 情绪主题配置（与需求文档 §11.5 对齐）。 */
export interface EmotionTheme {
  label: string;
  emoji: string;
  color: string;
  soft: string;
  score: number;
}

export type EmotionKey = 'happy' | 'calm' | 'low' | 'anxious' | 'angry';

export const EMOTION_THEME: Record<EmotionKey, EmotionTheme> = {
  happy: { label: '开心', emoji: '😊', color: '#4CAF50', soft: '#E8F5E9', score: 0.85 },
  calm: { label: '平静', emoji: '😌', color: '#90A4AE', soft: '#ECEFF1', score: 0.6 },
  low: { label: '低落', emoji: '😔', color: '#2196F3', soft: '#E3F2FD', score: 0.35 },
  anxious: { label: '焦虑', emoji: '😤', color: '#FF9800', soft: '#FFF3E0', score: 0.25 },
  angry: { label: '愤怒', emoji: '😡', color: '#F44336', soft: '#FFEBEE', score: 0.1 },
};

export const EMOTION_KEYS = Object.keys(EMOTION_THEME) as EmotionKey[];

/** 按标签名（中文）查找主题；找不到返回「平静」。 */
export function emotionByLabel(label?: string | null): EmotionTheme {
  const key = EMOTION_KEYS.find((k) => EMOTION_THEME[k].label === label);
  return key ? EMOTION_THEME[key] : EMOTION_THEME.calm;
}

/** 热力图色阶：红(0) → 黄(0.5) → 绿(1)。 */
export function heatColor(score: number | null | undefined): string {
  if (score == null) return '#ebedf0';
  const t = Math.max(0, Math.min(1, score));
  // 插值：红→黄→绿
  const r = t < 0.5 ? 244 : 76;
  const g = t < 0.5 ? 67 + (t * 2) * (255 - 67) : 175 + (t - 0.5) * 2 * (175 - 255) + 80;
  const b = t < 0.5 ? 54 + (t * 2) * (235 - 54) : 80;
  return `rgb(${Math.round(r)}, ${Math.round(Math.max(0, Math.min(255, g)))}, ${Math.round(Math.max(0, Math.min(255, b)))})`;
}
