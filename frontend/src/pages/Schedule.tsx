import { useEffect, useMemo, useState } from 'react';
import ScheduleHeatmap from '../components/schedule/ScheduleHeatmap';
import StatsOverview from '../components/schedule/StatsOverview';
import { useScheduleStore, type ScheduleItem } from '../store/schedule';
import { parseScheduleLine } from '../utils/plan';
import { formatDate } from '../utils/format';

const WEEKDAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

function toDateStr(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function toTimeStr(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatTimeFromIso(iso: string): string {
  return toTimeStr(new Date(iso));
}

/** 日程状态：已完成 / 已过期未完成 / 待办。 */
type ItemStatus = 'done' | 'overdue' | 'pending';

const STATUS_LABEL: Record<ItemStatus, string> = {
  done: '已完成',
  overdue: '已过期',
  pending: '待办',
};

function statusOf(it: ScheduleItem, nowTs: number): ItemStatus {
  if (it.done) return 'done';
  return new Date(it.due_at).getTime() < nowTs ? 'overdue' : 'pending';
}

export default function Schedule() {
  const { items, stats, loadRange, loadStats, add, toggle, remove } = useScheduleStore();
  const [weekOffset, setWeekOffset] = useState(0);
  const [content, setContent] = useState('');
  const [dueDate, setDueDate] = useState(() => toDateStr(new Date()));
  const [dueTime, setDueTime] = useState('20:00');
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState('');
  const [nowTs, setNowTs] = useState(() => Date.now());

  // 每分钟刷新一次当前时间，让「已过期」状态自动更新
  useEffect(() => {
    const t = setInterval(() => setNowTs(Date.now()), 60_000);
    return () => clearInterval(t);
  }, []);

  // 本周一（按 offset 前后翻周）
  const weekStart = useMemo(() => {
    const now = new Date();
    const cur = now.getDay();
    const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - ((cur + 6) % 7) + weekOffset * 7);
    return monday;
  }, [weekOffset]);

  const weekDays = useMemo(() => {
    const days: Date[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + i);
      days.push(d);
    }
    return days;
  }, [weekStart]);

  useEffect(() => {
    const end = new Date(weekStart);
    end.setDate(end.getDate() + 6);
    loadRange(formatDate(weekStart.toISOString()), formatDate(end.toISOString()));
  }, [weekStart, loadRange]);

  // 统计概览 + 热力图（进入页面即加载）
  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // 按本地日期分组
  const byDay = useMemo(() => {
    const map: Record<string, ScheduleItem[]> = {};
    for (const it of items) {
      const key = formatDate(it.due_at);
      (map[key] ??= []).push(it);
    }
    return map;
  }, [items]);

  const today = toDateStr(new Date());

  /** 批量添加：每行一条，自动解析行内日期/时间；没写时间的行用右侧默认日期+时间。 */
  const submit = async () => {
    const raw = content.trim();
    if (!raw || adding) return;
    setAdding(true);
    try {
      const fallbackHour = Number(dueTime.split(':')[0] ?? '20');
      const lines = raw
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      let ok = 0;
      const failed: string[] = [];
      for (const line of lines) {
        const parsed = parseScheduleLine(line, dueDate, fallbackHour);
        if (parsed) {
          const created = await add(parsed.content, parsed.dueAt, 'manual');
          if (created) ok++;
          else failed.push(line);
        } else {
          failed.push(line);
        }
      }
      if (ok) {
        setContent('');
        setNotice(
          ok === lines.length
            ? `已添加 ${ok} 条日程 📅`
            : `已添加 ${ok} 条；${failed.length} 行未识别：${failed.join(' / ')}`,
        );
        setTimeout(() => setNotice(''), 4000);
      } else {
        setNotice('没有识别到有效日程，请每行写一条，如「8:30 背单词」「明天下午3点 写周报」');
        setTimeout(() => setNotice(''), 4000);
      }
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="schedule-page">
      <h2 className="page-title">📅 日程安排</h2>
      <p className="page-sub">自己定计划，聊天里提计划，小光都会帮你记住并按时提醒</p>

      {/* 统计概览：今日/本周完成率进度环 + 近 7 天柱状图 */}
      <div className="card">
        <div className="card-title">
          完成进度
          <span className="card-sub">打卡后自动刷新</span>
        </div>
        <StatsOverview stats={stats} />
      </div>

      {/* 日程完成热力图 */}
      <div className="card">
        <div className="card-title">
          完成热力图
          <span className="card-sub">近 90 天 · 天 × 时段</span>
        </div>
        {stats && stats.heatmap.length ? (
          <ScheduleHeatmap days={stats.heatmap} />
        ) : (
          <div className="empty-state">暂无热力图数据</div>
        )}
      </div>

      {/* 周导航 + 添加 */}
      <div className="card">
        <div className="card-title">
          <div className="week-nav">
            <button className="btn btn-ghost week-btn" onClick={() => setWeekOffset((o) => o - 1)}>
              ◀ 上一周
            </button>
            <span className="week-range">
              {formatDate(weekStart.toISOString())} ~ {formatDate(new Date(weekStart.getTime() + 6 * 86400000).toISOString())}
              {weekOffset === 0 && <span className="week-today">本周</span>}
            </span>
            <button className="btn btn-ghost week-btn" onClick={() => setWeekOffset((o) => o + 1)}>
              下一周 ▶
            </button>
          </div>
        </div>

        <div className="add-row">
          <textarea
            className="input add-content add-textarea"
            placeholder={'每行一条，可带时间与日期，例如：\n8:30 背单词\n明天下午3点 写周报\n晚上跑步'}
            value={content}
            rows={3}
            maxLength={300}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={(e) => {
              // Ctrl/Cmd + Enter 快速提交
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit();
            }}
          />
          <div className="add-fallback">
            <input
              className="input add-date"
              type="date"
              value={dueDate}
              title="内容里没写日期的日程，默认用这个日期"
              onChange={(e) => setDueDate(e.target.value)}
            />
            <input
              className="input add-time"
              type="time"
              value={dueTime}
              title="内容里没写时间的日程，默认用这个时间"
              onChange={(e) => setDueTime(e.target.value)}
            />
          </div>
          <button className="btn add-btn" onClick={submit} disabled={adding || !content.trim()}>
            {adding ? '添加中…' : '＋ 批量添加'}
          </button>
        </div>
        <div className="add-hint">没写时间的行会用右侧默认时间；可整体改日期 · Ctrl+Enter 快捷提交</div>
        {notice && <div className="schedule-notice">{notice}</div>}
      </div>

      {/* 周视图：7 天 */}
      <div className="week-grid">
        {weekDays.map((d, i) => {
          const key = toDateStr(d);
          const dayItems = byDay[key] ?? [];
          const isToday = key === today;
          return (
            <div className={`day-card${isToday ? ' today' : ''}`} key={key}>
              <div className="day-title">
                <span className="day-name">{WEEKDAY_LABELS[i]}</span>
                <span className="day-date">{key.slice(5)}</span>
                {isToday && <span className="day-badge">今天</span>}
              </div>
              <div className="day-timeline">
                {dayItems.length ? (
                  dayItems.map((it) => {
                    const st = statusOf(it, nowTs);
                    return (
                      <div className={`tl-item ${st}`} key={it.id}>
                        <div className="tl-marker">
                          <span className="tl-dot" />
                        </div>
                        <div className="tl-body">
                          <div className="tl-time">
                            {formatTimeFromIso(it.due_at)}
                            <span className={`tl-tag ${st}`}>{STATUS_LABEL[st]}</span>
                          </div>
                          <div className="tl-content">{it.content}</div>
                          <div className="tl-meta">
                            {it.source === 'chat' && <span className="tl-src">来自对话</span>}
                            <label className="schedule-check">
                              <input
                                type="checkbox"
                                checked={it.done}
                                onChange={(e) => toggle(it.id, e.target.checked)}
                              />
                              <span>完成</span>
                            </label>
                          </div>
                        </div>
                        <button className="schedule-del" title="删除" onClick={() => remove(it.id)}>
                          ✕
                        </button>
                      </div>
                    );
                  })
                ) : (
                  <div className="day-empty">暂无安排</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
