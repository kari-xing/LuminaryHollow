import { useEffect, useState } from 'react';
import client from '../api/client';
import HeatmapCalendar from '../components/dashboard/HeatmapCalendar';
import TrendChart from '../components/dashboard/TrendChart';
import TimelineCard from '../components/dashboard/TimelineCard';
import WordCloud from '../components/dashboard/WordCloud';
import { useDashStore } from '../store/dashboard';

export default function Dashboard() {
  const [days, setDays] = useState(30);
  const { heatmap, trend, wordcloud, timeline } = useDashStore();

  useEffect(() => {
    (async () => {
      const year = new Date().getFullYear();
      const [h, t, w, tl] = await Promise.all([
        client.get('/dashboard/heatmap', { params: { year } }),
        client.get('/dashboard/trend', { params: { days } }),
        client.get('/dashboard/wordcloud', { params: { period: 'month' } }),
        client.get('/dashboard/timeline', { params: { page: 1, page_size: 10 } }),
      ]);
      useDashStore.setState({
        heatmap: h.data.days,
        trend: t.data.points,
        wordcloud: w.data.words,
        timeline: tl.data.items,
      });
    })();
  }, [days]);

  return (
    <div className="dash-page">
      <h2 className="page-title">📊 心情看板</h2>
      <p className="page-sub">把情绪变成看得见的风景</p>

      <div className="card">
        <div className="card-title">
          情绪热力图
          <span className="year-badge">{new Date().getFullYear()}</span>
        </div>
        <HeatmapCalendar days={heatmap} />
      </div>

      <div className="card">
        <div className="card-title">
          情绪趋势
          <div className="seg">
            {[30, 90].map((d) => (
              <button
                key={d}
                className={`seg-btn ${days === d ? 'active' : ''}`}
                onClick={() => setDays(d)}
              >
                近 {d} 天
              </button>
            ))}
          </div>
        </div>
        <TrendChart points={trend} />
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">关键词云</div>
          {wordcloud.length ? (
            <WordCloud words={wordcloud} />
          ) : (
            <div className="empty-state">还没有足够的高频词</div>
          )}
        </div>
        <div className="card">
          <div className="card-title">每日摘要</div>
          <TimelineCard items={timeline as { date: string; summary?: string | null }[]} />
        </div>
      </div>
    </div>
  );
}
