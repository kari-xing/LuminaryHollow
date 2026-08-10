import { create } from 'zustand';

export interface HeatmapDay {
  date: string;
  avg_score: number | null;
  count: number;
  label_mode?: string | null;
}

export interface TrendPoint {
  date: string;
  avg_score: number | null;
}

interface DashboardState {
  heatmap: HeatmapDay[];
  trend: TrendPoint[];
  wordcloud: { text: string; weight: number }[];
  timeline: unknown[];
  loading: boolean;
  setHeatmap: (days: HeatmapDay[]) => void;
  setTrend: (points: TrendPoint[]) => void;
  setWordcloud: (words: { text: string; weight: number }[]) => void;
  setTimeline: (items: unknown[]) => void;
  setLoading: (v: boolean) => void;
}

export const useDashStore = create<DashboardState>((set) => ({
  heatmap: [],
  trend: [],
  wordcloud: [],
  timeline: [],
  loading: false,
  setHeatmap: (days) => set({ heatmap: days }),
  setTrend: (points) => set({ trend: points }),
  setWordcloud: (words) => set({ wordcloud: words }),
  setTimeline: (items) => set({ timeline: items }),
  setLoading: (v) => set({ loading: v }),
}));
