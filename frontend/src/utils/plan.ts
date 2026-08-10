/**
 * 对话 → 日程：识别「带时间的计划」短语，并解析出计划时间（中文时间词 → Date）。
 */

/** 数字（含中文数字「二十五」=25）正则片段。 */
const NUM = '[0-9零一二两三四五六七八九十]+';

/** 识别带时间的计划短语：时间词 + 可选动词 + 行动内容（兼容「晚上学数学」这类口语省略）。 */
export const PLAN_DUE_PATTERN = new RegExp(
  '(?:今天|明天|后天|周末|今晚|深夜|凌晨|清晨|早晨|午间|夜里|晚间|(?:下|上|这)?周[一二三四五六日天]|下午|上午|中午|晚上|早上|' +
    NUM +
    '点)[^，。！？；、]{0,8}?(?:要|去|得|该|打算|准备|记得|计划|想|希望|安排|开始)?[^，。！？；、]{1,14}',
  'g',
);

const WEEKDAY: Record<string, number> = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 日: 0, 天: 0 };

const CN_NUM: Record<string, number> = { 零: 0, 一: 1, 二: 2, 两: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10 };

/** 中文数字 → 数字（「二十五」=25，「十」=10）。 */
function cnToNum(s: string): number {
  if (/^\d+$/.test(s)) return Number(s);
  let sum = 0;
  let buf = 0;
  for (const ch of s) {
    if (ch === '十') {
      sum += (buf === 0 ? 1 : buf) * 10;
      buf = 0;
    } else {
      buf = CN_NUM[ch] ?? 0;
    }
  }
  return sum + buf;
}

/** 匹配「X点 / X点X分 / X点半」，返回 [hour, minute?]。 */
function matchPointTime(text: string): [number, number | null] | null {
  const m = text.match(new RegExp('(' + NUM + ')点(?:(?:(' + NUM + ')分?|半))?'));
  if (!m) return null;
  const minute = m[2] != null ? cnToNum(m[2]) : /半/.test(text) ? 30 : null;
  return [cnToNum(m[1]), minute];
}

/** 短语里是否有显式的具体时间（"8点 / 三点半 / 20:00 / 七时"），用于判断是否要追问时间。 */
export function hasExplicitTime(text: string): boolean {
  return new RegExp('(' + NUM + ')点(?:(?:' + NUM + ')分?|半)?|(\\d{1,2}):(\\d{2})|(' + NUM + ')时').test(text);
}

/** 日期/时间词，用于从短语里剥离出「纯内容」。 */
const TIME_WORDS_RE = new RegExp(
  '今天|明天|后天|明儿|明日|周末|今晚|凌晨|深夜|清晨|早晨|早上|上午|中午|午间|下午|晚上|夜里|晚间|(?:下|上|这)?周[一二三四五六日天]|(' +
    NUM +
    ')点(?:(?:' +
    NUM +
    ')分?|半)?|(?:\\d{1,2}):(?:\\d{2})',
  'g',
);

/** 疑问句线索：像是「下午要干什么」这种问句，不算计划。 */
export const QUESTION_HINTS = /干什么|做什么|干嘛|啥|什么|几点|怎么|要不要|是不是|吗$|呢$|吧$|哪/;

/** 查询日程/安排的短语（「今天的日程安排」「把今天的日程发我」），不是计划。 */
const SCHEDULE_QUERY_PHRASE = /日程安排|的日程|的安排|的待办|日程|待办|事项|安排是/;

/** 动作特征词：内容里至少含一个才算「计划」，过滤「今天天气不错」这类状态描述。 */
const ACTION_WORDS =
  /要|去|得|该|打算|准备|记得|计划|想|希望|安排|开始|学|看|读|写|背|练|打|跑|走|来|买|卖|约|见|开|上|下|做|吃|喝|听|说|复习|预习|锻炼|健身|跑步|加班|开会|面试|考试|上课|上班|运动|购物|休息|睡觉|起床|出发|体检|复诊|爬山|散步|遛狗|取|寄|修|洗|刷|整理|收拾|学习|工作/;

/** 从短语解析计划时间；解析不到返回 null。 */
export function parsePlanDue(text: string): Date | null {
  const now = new Date();
  const base = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  let dayOffset = 0;

  if (/后天/.test(text)) dayOffset = 2;
  else if (/明天|明儿/.test(text)) dayOffset = 1;
  else if (/今天|今晚|今日/.test(text)) dayOffset = 0;

  const week = text.match(/(下|上|这)?周([一二三四五六日天])/);
  if (week) {
    const target = WEEKDAY[week[2]];
    const cur = base.getDay();
    let diff = (target - cur + 7) % 7;
    if (week[1] === '下') diff += 7;
    else if (week[1] === '上') diff -= 7;
    if (diff === 0 && !week[1]) diff = 7; // 无前缀且今天就是该周几 → 视为下一周
    base.setDate(base.getDate() + diff);
  } else {
    base.setDate(base.getDate() + dayOffset);
  }

  let hour = 20;
  let minute = 0;
  const hm = matchPointTime(text);
  if (hm) {
    hour = hm[0];
    minute = hm[1] ?? 0;
    // 下午/晚上/夜里/晚间 → 加 12 小时（「下午3点」应为 15:00；深夜/凌晨不加）
    if (/下午|晚上|夜里|晚间/.test(text) && hour < 12) hour += 12;
  } else if (/凌晨/.test(text)) hour = 5;
  else if (/清晨|早上|早晨/.test(text)) hour = 8;
  else if (/上午/.test(text)) hour = 10;
  else if (/中午|午间/.test(text)) hour = 12;
  else if (/下午/.test(text)) hour = 15;
  else if (/深夜/.test(text)) hour = 23;
  else if (/晚上|夜里|晚间/.test(text)) hour = 20;

  base.setHours(hour, minute, 0, 0);
  // 无日期词且时间已过 → 视为明天
  if (dayOffset === 0 && !week && base.getTime() < now.getTime()) {
    base.setDate(base.getDate() + 1);
  }
  return base;
}

export interface DuePlan {
  content: string;
  dueAt: string;
  /** 是否没有明确「几点」（如「晚上要学数学」），需要追问时间。 */
  timeGuess: boolean;
}

/** 从消息内容提取「带时间的计划」列表（去重保序）。
 * 兼容省略说法（「晚上学数学」）；排除疑问句（「下午要干什么」）与纯描述（「今天天气不错」）。
 */
export function extractDuePlans(content: string): DuePlan[] {
  const out: DuePlan[] = [];
  PLAN_DUE_PATTERN.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = PLAN_DUE_PATTERN.exec(content)) !== null) {
    const phrase = m[0].trim();
    // 疑问句（「下午要干什么」「晚上吃什么」）不算计划
    if (QUESTION_HINTS.test(phrase)) continue;
    // 查询日程/安排的句子（「今天的日程安排」）不算计划，只是向小光要日程
    if (SCHEDULE_QUERY_PHRASE.test(phrase)) continue;
    // 剥离时间词后，内容需含动作特征才算计划（过滤「今天天气不错」）
    const rest = phrase.replace(TIME_WORDS_RE, '').trim();
    if (rest.length < 2 || !ACTION_WORDS.test(rest)) continue;
    const due = parsePlanDue(phrase);
    if (due && !out.some((p) => p.content === phrase)) {
      out.push({ content: phrase, dueAt: due.toISOString(), timeGuess: !hasExplicitTime(phrase) });
    }
  }
  return out;
}

export interface ScheduleLineResult {
  content: string;
  dueAt: string;
  /** 行内是否自带具体时间（无需追问/回退默认）。 */
  timeGuess: boolean;
}

/**
 * 手动批量添加：把「一行一条」的日程行解析成 (内容, 到期时间)。
 *
 * - 日期：行内「明天 / 后天 / 周X / 周末」优先，否则用 fallbackDate（YYYY-MM-DD）
 * - 时间：行内「8:30 / 下午3点 / 三点半 / 晚上」优先，否则用 fallbackHour
 * - 内容：去掉时间/日期词后剩余文本；为空则视为无效行
 */
export function parseScheduleLine(
  line: string,
  fallbackDate: string,
  fallbackHour: number,
): ScheduleLineResult | null {
  const text = line.trim();
  if (!text) return null;
  const base = new Date(`${fallbackDate}T00:00:00`);
  if (Number.isNaN(base.getTime())) return null;

  // —— 日期 ——
  if (/后天/.test(text)) base.setDate(base.getDate() + 2);
  else if (/明天|明儿|明日/.test(text)) base.setDate(base.getDate() + 1);

  const week = text.match(/(下|上)?周([一二三四五六日天])/);
  if (week) {
    const target = WEEKDAY[week[2]];
    const cur = base.getDay();
    let diff = (target - cur + 7) % 7;
    if (week[1] === '下') diff += 7;
    else if (week[1] === '上') diff -= 7;
    if (diff === 0 && !week[1]) diff = 7; // 本周同日 → 视为下周
    base.setDate(base.getDate() + diff);
  } else if (/周末/.test(text)) {
    const cur = base.getDay();
    let diff = (6 - cur + 7) % 7; // 到下一个周六
    if (cur === 0) diff = 6; // 今天是周日 → 下周六
    base.setDate(base.getDate() + diff);
  }

  // —— 时间 ——
  let hour = fallbackHour;
  let minute = 0;
  let hasOwnTime = false;
  const hm24 = text.match(/(\d{1,2}):(\d{2})/);
  if (hm24) {
    hour = Number(hm24[1]);
    minute = Number(hm24[2]);
    hasOwnTime = true;
  } else {
    const hm = matchPointTime(text);
    if (hm) {
      hour = hm[0];
      minute = hm[1] ?? 0;
      if (/下午|晚上|夜里|晚间/.test(text) && hour < 12) hour += 12;
      hasOwnTime = true;
    } else if (/凌晨/.test(text)) hour = 5;
    else if (/清晨|早上|早晨/.test(text)) hour = 8;
    else if (/上午/.test(text)) hour = 10;
    else if (/中午|午间/.test(text)) hour = 12;
    else if (/下午/.test(text)) hour = 15;
    else if (/深夜/.test(text)) hour = 23;
    else if (/晚上|夜里|晚间/.test(text)) hour = 20;
  }
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;
  base.setHours(hour, minute, 0, 0);

  // —— 内容：去掉日期/时间词后剩余文本 ——
  const content = text
    .replace(/(\d{1,2}):(\d{2})/, '')
    .replace(TIME_WORDS_RE, '')
    .replace(/\s+/g, ' ')
    .trim();
  // 去掉标点后不足 2 个有效字符 → 视为无效行（如「!!!」）
  const meaningful = content.replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, '');
  if (content.length < 2 || meaningful.length < 2) return null;

  return { content, dueAt: base.toISOString(), timeGuess: !hasOwnTime };
}
