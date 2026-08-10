import { useMemo } from 'react';
import { heatColor } from '../../theme/emotion';
import { formatDate } from '../../utils/format';

/** GitHub 风格情绪热力图：每天一格，红→黄→绿。 */
export default function HeatmapCalendar({ days }: { days: { date: string; avg_score: number | null; count: number }[] }) {
  const weeks = useMemo(() => {
    if (!days.length) return [];
    // 按周分列（周日开头）
    const cols: { date: string; score: number | null; count: number }[][] = [];
    let col: { date: string; score: number | null; count: number }[] = [];
    const first = new Date(days[0].date);
    for (let i = 0; i < first.getDay(); i++) col.push({ date: '', score: null, count: 0 });
    for (const d of days) {
      col.push({ date: d.date, score: d.avg_score, count: d.count });
      if (new Date(d.date).getDay() === 6) {
        cols.push(col);
        col = [];
      }
    }
    if (col.length) cols.push(col);
    return cols;
  }, [days]);

  return (
    <div className="heatmap-wrap">
      <div className="heatmap">
        {weeks.map((week, i) => (
          <div className="heat-col" key={i}>
            {week.map((d, j) =>
              d.date ? (
                <div
                  key={d.date}
                  className="heat-cell"
                  style={{ background: heatColor(d.score) }}
                  title={`${formatDate(d.date)} · 情绪分 ${d.score ?? '—'} · ${d.count} 条`}
                />
              ) : (
                <div key={j} className="heat-cell empty" />
              ),
            )}
          </div>
        ))}
      </div>
      <div className="heat-legend">
        <span>少</span>
        <div className="heat-cell" style={{ background: heatColor(0) }} />
        <div className="heat-cell" style={{ background: heatColor(0.5) }} />
        <div className="heat-cell" style={{ background: heatColor(1) }} />
        <span>多</span>
      </div>
    </div>
  );
}
