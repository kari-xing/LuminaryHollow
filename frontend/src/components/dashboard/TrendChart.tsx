import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

/** 情绪趋势折线图（ECharts）：近 30/90 天日均情绪评分。 */
export default function TrendChart({ points }: { points: { date: string; avg_score: number | null }[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 20, bottom: 30 },
      xAxis: {
        type: 'category',
        data: points.map((p) => p.date.slice(5)),
        axisLabel: { interval: 'auto', fontSize: 10 },
      },
      yAxis: { type: 'value', min: 0, max: 1, splitLine: { lineStyle: { type: 'dashed' } } },
      series: [
        {
          name: '情绪评分',
          type: 'line',
          smooth: true,
          data: points.map((p) => p.avg_score),
          lineStyle: { color: '#6c5ce7', width: 2 },
          itemStyle: { color: '#6c5ce7' },
          areaStyle: { color: 'rgba(108, 92, 231, 0.12)' },
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [points]);

  return <div ref={ref} style={{ width: '100%', height: 280 }} />;
}
