/**
 * AI 拟人化配置：名字 / 在线状态 / 时段问候 / 长对话温馨提醒。
 * 让「小光」更有人的温度。
 */

/** AI 的名字与形象。 */
export const AI_NAME = '小光';
export const AI_EMOJI = '🕯️';
export const ONLINE_STATUS = '在线';

/** 按时段返回 { 开场问候语, 侧边栏状态语 }。 */
export function greetingByHour(hour: number): { text: string; status: string } {
  if (hour >= 5 && hour < 9) {
    return { text: '早安呀，新的一天。想从哪里说起？', status: '早上好' };
  }
  if (hour >= 9 && hour < 12) {
    return { text: '上午好，我在呢。今天想聊点什么？', status: '上午陪你' };
  }
  if (hour >= 12 && hour < 14) {
    return { text: '午安，吃过饭了吗？慢慢说，我听着。', status: '午间陪你' };
  }
  if (hour >= 14 && hour < 18) {
    return { text: '下午好呀，我一直在。今天过得怎么样？', status: '下午陪你' };
  }
  if (hour >= 18 && hour < 23) {
    return { text: '晚上好，忙了一整天了吧？我陪你说说话。', status: '晚上陪你' };
  }
  return { text: '夜深了，还不睡吗？我在这里陪着你。', status: '深夜值守' };
}

/** 长对话温馨提醒（按阈值循环使用，可打卡）。 */
export const REMINDER_MESSAGES: { icon: string; text: string }[] = [
  { icon: '☕', text: '聊了这么久，喝口水休息一下吧' },
  { icon: '🪟', text: '起来伸个懒腰，看看窗外透透气' },
  { icon: '🌿', text: '深呼吸一下，我就在这儿陪着你' },
  { icon: '🧘', text: '肩膀是不是有点紧？放松一下，慢慢来' },
];

/** 提醒打卡完成后的鼓励语。 */
export const REMINDER_DONE_REPLY = '真棒，好好照顾自己 🥰';

/** 最近已触发提醒的轮次存储键（localStorage，避免刷新后历史卡片重现、从下一轮继续冒卡）。 */
export const REMINDER_LAST_ROUND_KEY = 'luminary-reminders-last-round';

/** 每 N 轮真实对话提醒一次（第 8 / 16 / 24 … 轮）。 */
export const REMINDER_EVERY_ROUNDS = 8;

/** WorkBuddy：从用户消息中识别「要去干什么」的计划（正则 MVP）。 */
export const PLAN_PATTERN =
  /(?:我要|我得|我打算|我准备|准备去|记得|别忘了|计划|待会儿要|待会要|接下来要|明天要|下午要|晚上要|下周要|今天要|这个周末要)\s*(?:去|要|得|该)?\s*([^，。！？；、\s]{2,16})/g;

/** WorkBuddy 提醒文案。 */
export function workBuddyText(plan: string): string {
  return `你之前说「${plan}」——现在想起来了吗？`;
}

/** 每 N 轮真实对话提醒一次 WorkBuddy（复用贴心提醒卡片）。 */
export const WORKBUDDY_EVERY_ROUNDS = 5;
