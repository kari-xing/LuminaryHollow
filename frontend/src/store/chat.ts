import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  emotion_label?: string | null;
  emotion_score?: number | null;
  emotion_intensity?: number | null;
  is_quick_checkin?: boolean;
  created_at: string;
}

interface ChatState {
  sessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  isTyping: boolean;
  /** 流式输出的 AI 草稿（当前正在生成的完整内容） */
  draftContent: string;
  draftEmotion: { label: string; score: number; intensity: number } | null;
  setSession: (id: string | null) => void;
  loadMessages: (messages: ChatMessage[]) => void;
  appendUserMessage: (content: string) => void;
  beginStream: () => void;
  appendChunk: (chunk: string) => void;
  endStream: (emotion?: { label: string; score: number; intensity: number }) => void;
  setTyping: (v: boolean) => void;
  addQuickCheckin: (label: string) => void;
  clear: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessionId: null,
  messages: [],
  isStreaming: false,
  isTyping: false,
  draftContent: '',
  draftEmotion: null,

  setSession: (id) => set({ sessionId: id, messages: [], draftContent: '' }),
  loadMessages: (messages) => set({ messages }),
  appendUserMessage: (content) =>
    set({
      messages: [
        ...get().messages,
        { id: crypto.randomUUID(), role: 'user', content, created_at: new Date().toISOString() },
      ],
    }),
  beginStream: () => set({ isStreaming: true, isTyping: true, draftContent: '', draftEmotion: null }),
  appendChunk: (chunk) => set({ draftContent: get().draftContent + chunk }),
  endStream: (emotion?: { label: string; score: number; intensity: number }) =>
    set((state) => {
      const full = state.draftContent;
      const newMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: full,
        emotion_label: emotion?.label ?? null,
        emotion_score: emotion?.score ?? null,
        emotion_intensity: emotion?.intensity ?? null,
        created_at: new Date().toISOString(),
      };
      return {
        isStreaming: false,
        isTyping: false,
        draftContent: '',
        draftEmotion: emotion ?? null,
        messages: [...state.messages, newMsg],
      };
    }),
  setTyping: (v) => set({ isTyping: v }),
  addQuickCheckin: (label) =>
    set({
      messages: [
        ...get().messages,
        {
          id: crypto.randomUUID(),
          role: 'user',
          content: `[快捷情绪打卡] ${label}`,
          emotion_label: label,
          is_quick_checkin: true,
          created_at: new Date().toISOString(),
        },
      ],
    }),
  clear: () => set({ messages: [], draftContent: '', draftEmotion: null }),
}));
