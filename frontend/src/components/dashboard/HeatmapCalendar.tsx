import { useMemo } from 'react';
import { heatColor } from '../../theme/emotion';
import { formatDate } from '../../utils/format';
import type { HeatmapDay } from '../../store/dashboard';

/** 时段标签（每 3 小时一档，共 8 档）。 */
const SLOT_LABELS = ['0-3', '3-6', '6-9', '9-12', '12-15', '15-18', '18-21', '21-24'];

/**
 * 时段热力图：每天一列、8 个时段格（横轴天、纵轴时段）。
 * 相比天粒度热力图，能看出「上午低落、晚上开心」这类阶段性情绪规律。
 */
export default function HeatmapCalendar({ days }: { days: HeatmapDay[] }) {
  const weeks = useMemo(() => {
    if (!days.length) return [];
    // 按周分列（周日开头）
    const cols: (HeatmapDay | null)[][] = [];
    let col: (HeatmapDay | null)[] = [];
    const first = new Date(days[0].date);
    for (let i = 0; i < first.getDay(); i++) col.push(null); // 周初占位
    for (const d of days) {
      col.push(d);
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
      <div className="slot-heatmap">
        <div className="slot-labels">
          {SLOT_LABELS.map((l) => (
            <div key={l} className="slot-label">
              {l}点
            </div>
          ))}
        </div>
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
                        style={{ background: heatColor(s.avg_score) }}
                        title={`${formatDate(d.date)} ${SLOT_LABELS[s.slot]}点 · 情绪分 ${s.avg_score ?? '—'} · ${s.count} 条`}
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
      <div className="heat-legend">
        <span>少</span>
        <div className="heat-cell" style={{ background: heatColor(0) }} />
        <div className="heat-cell" style={{ background: heatColor(0.5) }} />
        <div className="heat-cell" style={{ background: heatColor(1) }} />
        <span>多</span>
      </div>
      <div className="heat-legend slot-hint">每一列代表一天，从上到下 8 个时段；悬停查看详情</div>
    </div>
  );
}
