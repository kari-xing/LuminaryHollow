import type { ScheduleStats } from '../../store/schedule';

/** 0~1 完成率 → 百分比（取整）。 */
function pct(v: number | null | undefined): number {
  if (v == null) return 0;
  return Math.max(0, Math.min(100, Math.round(v * 100)));
}

/** 环形进度图。 */
function Ring({
  label,
  sub,
  value,
  color,
}: {
  label: string;
  sub: string;
  value: number;
  color: string;
}) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const filled = (value / 100) * c;
  return (
    <div className="stat-ring-wrap">
      <div className="stat-ring">
        <svg width="108" height="108" viewBox="0 0 108 108" aria-hidden>
          <circle cx="54" cy="54" r={r} fill="none" stroke="var(--border)" strokeWidth="10" />
          <circle
            cx="54"
            cy="54"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${filled} ${c}`}
            transform="rotate(-90 54 54)"
          />
        </svg>
        <div className="stat-ring-num">{value}%</div>
      </div>
      <div className="stat-ring-label">{label}</div>
      <div className="stat-ring-sub">{sub}</div>
    </div>
  );
}

/** 统计概览：今日/本周完成率进度环 + 近 7 天完成柱状图。 */
export default function StatsOverview({ stats }: { stats: ScheduleStats | null }) {
  if (!stats) return <div className="empty-state">暂无统计数据，先添加几条日程吧 📅</div>;

  const todayPct = pct(stats.today.done_rate);
  const weekPct = pct(stats.week.done_rate);
  const maxDaily = Math.max(1, ...stats.daily.map((d) => d.total));

  return (
    <div className="stats-grid">
      <div className="stat-block ring-block">
        <Ring
          label="今日进度"
          sub={`${stats.today.done} / ${stats.today.total} 项`}
          value={todayPct}
          color="#34c759"
        />
        <Ring
          label="本周完成"
          sub={`${stats.week.done} / ${stats.week.total} 项`}
          value={weekPct}
          color="var(--primary)"
        />
      </div>

      <div className="stat-block bar-block">
        <div className="stat-title">近 7 天完成情况</div>
        <div className="bar-chart">
          {stats.daily.map((d) => (
            <div className="bar-col" key={d.date} title={`${d.date} · 完成 ${d.done} / ${d.total}`}>
              <div className="bar-track">
                <div
                  className="bar-fill done"
                  style={{ height: `${(d.done / maxDaily) * 100}%` }}
                />
                <div
                  className="bar-fill open"
                  style={{ height: `${((d.total - d.done) / maxDaily) * 100}%` }}
                />
              </div>
              <div className="bar-label">{d.date.slice(5)}</div>
            </div>
          ))}
        </div>
        <div className="bar-legend">
          <span>
            <i className="dot dot-done" />
            已完成
          </span>
          <span>
            <i className="dot dot-open" />
            未完成
          </span>
        </div>
      </div>
    </div>
  );
}
