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

  setSession: (id) =>
    set({
      sessionId: id,
      messages: [],
      draftContent: '',
      draftEmotion: null,
      isStreaming: false,
      isTyping: false,
    }),
  loadMessages: (messages) => set({ messages }),
  appendUserMessage: (content) =>
    set({
      messages: [
        ...get().messages,
        { id: crypto.randomUUID(), role: 'user', content, created_at: new Date().toISOString() },
      ],
    }),
  beginStream: () => set({ isStreaming: true, isTyping: true, draftContent: '', draftEmotion: null }),
  appendChunk: (chunk) =>
    set((state) => {
      // 防御：非流式状态收到 chunk（重复 handler / 迟到消息）直接忽略，防止重复追加
      if (!state.isStreaming || !chunk) return state;
      return { draftContent: state.draftContent + chunk };
    }),
  endStream: (emotion?: { label: string; score: number; intensity: number }) =>
    set((state) => {
      const full = state.draftContent;
      // 幂等保护：重复收到 stream_end（如 handler 重复注册）时，
      // 若草稿已清空或与上一条 AI 消息一致，只复位状态、不重复添加消息
      const lastMsg = state.messages[state.messages.length - 1];
      if (
        (lastMsg?.role === 'assistant' && lastMsg.content === full && full !== '') ||
        full === ''
      ) {
        return {
          isStreaming: false,
          isTyping: false,
          draftContent: '',
          draftEmotion: emotion ?? null,
        };
      }
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
