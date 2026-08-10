import { useMemo } from 'react';
import type { ScheduleHeatmapDay } from '../../store/schedule';

/** 时段标签（每 3 小时一档，共 8 档，与情绪热力图一致）。 */
const SLOT_LABELS = ['0-3', '3-6', '6-9', '9-12', '12-15', '15-18', '18-21', '21-24'];

/** 日程完成率色阶：无日程 → 浅灰；有日程按完成率 0~1 → 浅绿 ~ 深绿。 */
function doneColor(rate: number | null | undefined, total: number): string {
  if (!total) return '#f3f1fb';
  const t = rate ?? 0;
  return `rgba(52, 199, 89, ${0.16 + t * 0.84})`;
}

/** 本地日期（YYYY-MM-DD）→ Date，避免 ISO date-only 被按 UTC 解析跨天。 */
function parseLocalDay(s: string): Date {
  return new Date(`${s}T00:00:00`);
}

/**
 * 日程完成热力图：近 N 天，每天一列、8 个时段格。
 * 绿色越深代表该时段的日程完成率越高，能直观看出「哪个时间段最容易拖到没完成」。
 */
export default function ScheduleHeatmap({ days }: { days: ScheduleHeatmapDay[] }) {
  const weeks = useMemo(() => {
    if (!days.length) return [];
    const cols: (ScheduleHeatmapDay | null)[][] = [];
    let col: (ScheduleHeatmapDay | null)[] = [];
    const first = parseLocalDay(days[0].date);
    for (let i = 0; i < first.getDay(); i++) col.push(null); // 周初占位（周日开头）
    for (const d of days) {
      col.push(d);
      if (parseLocalDay(d.date).getDay() === 6) {
        cols.push(col);
        col = [];
      }
    }
    if (col.length) cols.push(col);
    return cols;
  }, [days]);

  return (
    <div className="heatmap-wrap">
      <div className="slot-heatmap">
        <div className="slot-labels">
          {SLOT_LABELS.map((l) => (
            <div key={l} className="slot-label">
              {l}点
            </div>
          ))}
        </div>
        <div className="sched-heatmap-scroll">
          <div className="heatmap slot">
            {weeks.map((week, i) => (
              <div className="heat-col slot" key={i}>
                {week.map((d, j) =>
                  d ? (
                    <div className="slot-stack" key={d.date}>
                      {d.slots.map((s) => (
                        <div
                          key={s.slot}
                          className="heat-cell"
                          style={{ background: doneColor(s.done_rate, s.total) }}
                          title={`${d.date} ${SLOT_LABELS[s.slot]}点 · 完成 ${s.done}/${s.total} · ${s.done_rate != null ? Math.round(s.done_rate * 100) + '%' : '—'}`}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="slot-stack" key={j}>
                      {SLOT_LABELS.map((_, si) => (
                        <div key={si} className="heat-cell empty" />
                      ))}
                    </div>
                  ),
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="heat-legend">
        <span>无日程</span>
        <div className="heat-cell" style={{ background: doneColor(0, 1) }} />
        <div className="heat-cell" style={{ background: doneColor(0.5, 1) }} />
        <div className="heat-cell" style={{ background: doneColor(1, 1) }} />
        <span>全完成</span>
      </div>
      <div className="heat-legend slot-hint">每一列代表一天，从上到下 8 个时段；绿色越深完成率越高，悬停查看详情</div>
    </div>
  );
}
