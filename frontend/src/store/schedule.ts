import { create } from 'zustand';
import client from '../api/client';

export interface ScheduleItem {
  id: string;
  content: string;
  due_at: string;
  done: boolean;
  source: 'manual' | 'chat';
  created_at: string;
}

export interface ScheduleStat {
  date: string;
  total: number;
  done: number;
  done_rate: number | null;
}

export interface ScheduleSlotStat {
  slot: number;
  total: number;
  done: number;
  done_rate: number | null;
}

export interface ScheduleHeatmapDay {
  date: string;
  total: number;
  done: number;
  done_rate: number | null;
  slots: ScheduleSlotStat[];
}

export interface ScheduleStats {
  today: ScheduleStat;
  week: { start: string; end: string; total: number; done: number; done_rate: number | null };
  daily: ScheduleStat[];
  heatmap: ScheduleHeatmapDay[];
}

interface ScheduleState {
  items: ScheduleItem[];
  stats: ScheduleStats | null;
  statsLoading: boolean;
  /** 按本地日期范围加载（start/end 为 YYYY-MM-DD）。 */
  loadRange: (start: string, end: string) => Promise<void>;
  /** 新增（手动 source=manual / 对话自动补充 source=chat）。 */
  add: (content: string, dueAt: string, source?: 'manual' | 'chat') => Promise<ScheduleItem | null>;
  /** 完成/取消完成。 */
  toggle: (id: string, done: boolean) => Promise<void>;
  /** 修改日程时间（如对话里"几点开始"确认后）。 */
  updateDue: (id: string, dueAt: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  /** 加载统计概览 + 完成热力图（本地时区聚合）。 */
  loadStats: (days?: number, heatDays?: number) => Promise<void>;
  /** 完成打卡后刷新统计，让进度环 / 热力图即时更新。 */
  refreshStats: () => Promise<void>;
}

export const useScheduleStore = create<ScheduleState>((set, get) => ({
  items: [],
  stats: null,
  statsLoading: false,

  loadRange: async (start, end) => {
    try {
      const { data } = await client.get('/schedule', { params: { start, end } });
      set({ items: data.items });
    } catch {
      /* 忽略加载失败 */
    }
  },

  add: async (content, dueAt, source = 'manual') => {
    try {
      const { data } = await client.post('/schedule', { content, due_at: dueAt, source });
      set({
        items: [...get().items, data].sort((a, b) => a.due_at.localeCompare(b.due_at)),
      });
      get().refreshStats();
      return data;
    } catch {
      return null;
    }
  },

  toggle: async (id, done) => {
    set({ items: get().items.map((it) => (it.id === id ? { ...it, done } : it)) });
    try {
      await client.put(`/schedule/${id}`, { done });
    } catch {
      /* 忽略 */
    }
    get().refreshStats();
  },

  updateDue: async (id, dueAt) => {
    set({ items: get().items.map((it) => (it.id === id ? { ...it, due_at: dueAt } : it)) });
    try {
      await client.put(`/schedule/${id}`, { due_at: dueAt });
    } catch {
      /* 忽略 */
    }
    get().refreshStats();
  },

  remove: async (id) => {
    set({ items: get().items.filter((it) => it.id !== id) });
    try {
      await client.delete(`/schedule/${id}`);
    } catch {
      /* 忽略 */
    }
    get().refreshStats();
  },

  loadStats: async (days = 7, heatDays = 90) => {
    if (get().statsLoading) return;
    set({ statsLoading: true });
    try {
      const { data } = await client.get('/schedule/stats', { params: { days, heat_days: heatDays } });
      set({ stats: data });
    } catch {
      /* 忽略加载失败 */
    } finally {
      set({ statsLoading: false });
    }
  },

  refreshStats: async () => {
    await get().loadStats();
  },
}));
