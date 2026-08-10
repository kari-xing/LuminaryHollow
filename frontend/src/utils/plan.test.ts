import { describe, it, expect } from 'vitest';
import { parsePlanDue, extractDuePlans, parseScheduleLine } from './plan';

describe('parsePlanDue 中文时间解析', () => {
  it('解析「明天下午3点」→ 明天 15:00', () => {
    const due = parsePlanDue('明天下午3点要去开会')!;
    const expected = new Date();
    expected.setDate(expected.getDate() + 1);
    expected.setHours(15, 0, 0, 0);
    expect(due.getTime()).toBe(expected.getTime());
  });

  it('解析「周六去跑步」→ 下一个周六 20:00', () => {
    const due = parsePlanDue('周六去跑步')!;
    const now = new Date();
    let diff = (6 - now.getDay() + 7) % 7;
    if (diff === 0) diff = 7;
    const expected = new Date(now.getFullYear(), now.getMonth(), now.getDate() + diff, 20, 0, 0, 0);
    expect(due.getTime()).toBe(expected.getTime());
  });

  it('解析「晚上8点」→ 今天或明天 20:00', () => {
    const due = parsePlanDue('晚上8点要写周报')!;
    expect(due.getHours()).toBe(20);
    expect(due.getMinutes()).toBe(0);
    const now = new Date();
    const today20 = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 20, 0, 0, 0);
    const expected = today20.getTime() < now.getTime() ? today20.getTime() + 86400000 : today20.getTime();
    expect(due.getTime()).toBe(expected);
  });

  it('解析「下周一下午2点半」→ 下周一 14:30', () => {
    const due = parsePlanDue('下周一下午2点半要去开会')!;
    const now = new Date();
    let diff = (1 - now.getDay() + 7) % 7; // 目标周一
    diff += 7; // 下周
    const expected = new Date(now.getFullYear(), now.getMonth(), now.getDate() + diff, 14, 30, 0, 0);
    expect(due.getTime()).toBe(expected.getTime());
  });
});

describe('extractDuePlans 从对话提取日程', () => {
  it('识别「明天上午要去医院」', () => {
    const plans = extractDuePlans('我明天上午要去医院复诊');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    const p = plans[0];
    expect(p.content).toContain('医院');
    expect(new Date(p.dueAt).getHours()).toBe(10);
  });

  it('识别「下午三点要开周会」', () => {
    const plans = extractDuePlans('下午三点要开周会');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    const p = plans[0];
    expect(p.content).toContain('周会');
    expect(new Date(p.dueAt).getHours()).toBe(15);
  });

  it('没有计划动词的句子不提取', () => {
    expect(extractDuePlans('今天心情不错')).toEqual([]);
  });
});

describe('extractDuePlans 识别「想/希望」类计划与时间追问标记', () => {
  it('「我晚上想学数学」应被提取（动词「想」）', () => {
    const plans = extractDuePlans('我晚上想学数学');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    const p = plans[0];
    expect(p.content).toContain('学数学');
    expect(p.timeGuess).toBe(true); // 没有明确几点 → 需要反问
    expect(new Date(p.dueAt).getHours()).toBe(20);
  });

  it('「晚上要学数学」timeGuess=true（没有明确几点）', () => {
    const plans = extractDuePlans('晚上要学数学');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    expect(plans[0].timeGuess).toBe(true);
  });

  it('「晚上8点要写周报」timeGuess=false（有明确时间）', () => {
    const plans = extractDuePlans('晚上8点要写周报');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    expect(plans[0].timeGuess).toBe(false);
  });

  it('「明天希望早点睡」可提取', () => {
    const plans = extractDuePlans('明天希望早点睡');
    expect(plans.length).toBeGreaterThanOrEqual(1);
  });
});

describe('extractDuePlans 省略说法与误报过滤', () => {
  it('「晚上学数学」（无动词省略说法）应被提取', () => {
    const plans = extractDuePlans('晚上学数学');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    const p = plans[0];
    expect(p.content).toContain('学数学');
    expect(new Date(p.dueAt).getHours()).toBe(20);
    expect(p.timeGuess).toBe(true);
  });

  it('「我就晚上学数学」也能提取', () => {
    const plans = extractDuePlans('我就晚上学数学');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    expect(plans[0].content).toContain('学数学');
  });

  it('「下午要干什么」是疑问句，不提取', () => {
    expect(extractDuePlans('下午要干什么')).toEqual([]);
  });

  it('「晚上吃什么」是疑问句，不提取', () => {
    expect(extractDuePlans('晚上吃什么')).toEqual([]);
  });

  it('「明天有什么安排」不提取', () => {
    expect(extractDuePlans('明天有什么安排')).toEqual([]);
  });

  it('「今天天气不错」是状态描述，不提取', () => {
    expect(extractDuePlans('今天天气不错')).toEqual([]);
  });

  it('「今天的日程安排」是向小光要日程，不作为计划', () => {
    expect(extractDuePlans('今天的日程安排')).toEqual([]);
  });

  it('「把今天的日程发我」是查询，不作为计划', () => {
    expect(extractDuePlans('把今天的日程发我')).toEqual([]);
  });

  it('「今天有什么安排」是查询，不作为计划', () => {
    expect(extractDuePlans('今天有什么安排')).toEqual([]);
  });

  it('「今天安排去爬山」仍是计划，不误伤', () => {
    const plans = extractDuePlans('今天安排去爬山');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    expect(plans[0].content).toContain('爬山');
  });

  it('「下午三点要开周会」中文数字也算明确时间 → timeGuess=false', () => {
    const plans = extractDuePlans('下午三点要开周会');
    expect(plans.length).toBeGreaterThanOrEqual(1);
    expect(plans[0].timeGuess).toBe(false);
  });

  it('「晚上七点要背单词」中文数字七 → 19:00', () => {
    const due = parsePlanDue('晚上七点要背单词')!;
    expect(due.getHours()).toBe(19);
  });

  it('「下午三点半开会」→ 15:30', () => {
    const due = parsePlanDue('下午三点半开会')!;
    expect(due.getHours()).toBe(15);
    expect(due.getMinutes()).toBe(30);
  });
});

describe('parseScheduleLine 批量添加解析', () => {
  it('解析「8:30 背单词」→ 内容与精确时间', () => {
    const r = parseScheduleLine('8:30 背单词', '2026-08-10', 20)!;
    expect(r.content).toBe('背单词');
    expect(r.timeGuess).toBe(false);
    const d = new Date(r.dueAt);
    expect(d.getHours()).toBe(8);
    expect(d.getMinutes()).toBe(30);
  });

  it('解析「明天下午3点 写周报」→ 明天 15:00', () => {
    const r = parseScheduleLine('明天下午3点 写周报', '2026-08-10', 20)!;
    expect(r.content).toBe('写周报');
    const d = new Date(r.dueAt);
    expect(d.getDate()).toBe(11);
    expect(d.getHours()).toBe(15);
  });

  it('没写时间的行用默认时间', () => {
    const r = parseScheduleLine('跑步', '2026-08-10', 20)!;
    expect(r.content).toBe('跑步');
    expect(r.timeGuess).toBe(true);
    const d = new Date(r.dueAt);
    expect(d.getDate()).toBe(10);
    expect(d.getHours()).toBe(20);
  });

  it('解析「周三下午开会」→ 下一个周三 15:00', () => {
    // 2026-08-10 是周一 → 本周三 8/12
    const r = parseScheduleLine('周三下午开会', '2026-08-10', 20)!;
    expect(r.content).toBe('开会');
    const d = new Date(r.dueAt);
    expect(d.getDate()).toBe(12);
    expect(d.getHours()).toBe(15);
  });

  it('解析「周末去爬山」→ 下一个周六', () => {
    const r = parseScheduleLine('周末去爬山', '2026-08-10', 20)!;
    expect(r.content).toBe('去爬山');
    const d = new Date(r.dueAt);
    expect(d.getDay()).toBe(6); // 周六
    expect(d.getDate()).toBe(15);
  });

  it('无效行返回 null', () => {
    expect(parseScheduleLine('!!!', '2026-08-10', 20)).toBeNull();
    expect(parseScheduleLine('', '2026-08-10', 20)).toBeNull();
  });
});
