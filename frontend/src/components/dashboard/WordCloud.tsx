import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import 'echarts-wordcloud';

/** 关键词云（ECharts wordcloud 扩展）。 */
export default function WordCloud({ words }: { words: { text: string; weight: number }[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    if (!words.length) {
      chart.clear();
      return () => chart.dispose();
    }
    chart.setOption({
      tooltip: {},
      series: [
        {
          type: 'wordCloud',
          shape: 'circle',
          sizeRange: [12, 42],
          rotationRange: [0, 0],
          textStyle: { color: () => `hsl(${Math.floor(Math.random() * 360)}, 65%, 55%)` },
          data: words,
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [words]);

  return (
    <div className="wordcloud">
      <div ref={ref} style={{ width: '100%', height: 220 }} />
    </div>
  );
}
