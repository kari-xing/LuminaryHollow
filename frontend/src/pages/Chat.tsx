import { useEffect, useRef, useState } from 'react';
import client from '../api/client';
import { useAuthStore } from '../store/auth';
import { useChatStore } from '../store/chat';
import { wsManager } from '../ws/manager';
import MessageBubble, { QuickEmotionPicker } from '../components/chat/MessageBubble';
import InputBar from '../components/chat/InputBar';
import TypingIndicator from '../components/chat/TypingIndicator';
import { emotionByLabel } from '../theme/emotion';

export default function Chat() {
  const token = useAuthStore((s) => s.accessToken);
  const sessionId = useChatStore((s) => s.sessionId);
  const setSession = useChatStore((s) => s.setSession);
  const messages = useChatStore((s) => s.messages);
  const draft = useChatStore((s) => s.draftContent);
  const draftEmotion = useChatStore((s) => s.draftEmotion);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  // 1. 初始化会话（不存在则创建）
  useEffect(() => {
    if (!token) return;
    (async () => {
      if (!sessionId) {
        const { data } = await client.post('/sessions');
        setSession(data.id);
      } else {
        // 切换/刷新时加载历史消息
        const { data } = await client.get(`/sessions/${sessionId}`);
        setSession(sessionId);
        useChatStore.getState().loadMessages(data.messages);
      }
    })();
  }, [sessionId, token, setSession]);

  // 2. WebSocket 连接与消息路由
  useEffect(() => {
    if (!sessionId || !token) return;
    wsManager.connect(sessionId, token);
    const unsub = wsManager.onMessage((msg) => {
      const chat = useChatStore.getState();
      switch (msg.type) {
        case 'typing':
          chat.setTyping(true);
          break;
        case 'stream_chunk':
          chat.appendChunk(msg.content ?? '');
          break;
        case 'stream_end':
          chat.endStream(
            msg.emotion_label ? { label: msg.emotion_label, score: msg.emotion_score ?? 0.5 } : undefined,
          );
          break;
        case 'quick_ok':
          break;
        case 'error':
          chat.endStream();
          break;
      }
    });
    return () => unsub();
  }, [sessionId, token]);

  // 3. 自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, draft]);

  const send = () => {
    const content = input.trim();
    if (!content || isStreaming) return;
    setInput('');
    useChatStore.getState().appendUserMessage(content);
    useChatStore.getState().beginStream();
    const ok = wsManager.send({ type: 'user_message', content });
    if (!ok) useChatStore.getState().endStream(); // 连接断开时兜底
  };

  const quickCheckin = (label: string) => {
    useChatStore.getState().addQuickCheckin(label);
    wsManager.send({ type: 'quick_checkin', emotion_label: label });
  };

  const newConversation = async () => {
    const { data } = await client.post('/sessions');
    setSession(data.id);
  };

  const draftTheme = emotionByLabel(draftEmotion?.label);
  const showDraft = isStreaming && draft;

  return (
    <div className="chat-page">
      <div className="chat-header">
        <h2>💬 聊天</h2>
        <button className="btn btn-ghost" onClick={newConversation}>
          ✨ 新对话
        </button>
      </div>

      <div className="chat-window card">
        <div className="chat-list">
          {messages.length === 0 && !showDraft && (
            <div className="chat-empty">
              <div className="empty-emoji">🕯️</div>
              <p>这里是只属于你的树洞。</p>
              <p className="page-sub">把心事说出来，我会认真记住、好好陪着你。</p>
            </div>
          )}

          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              role={m.role}
              content={m.content}
              emotionLabel={m.emotion_label}
              isPrivate={m.is_quick_checkin ? false : undefined}
              isQuickCheckin={m.is_quick_checkin}
            />
          ))}

          {showDraft && (
            <div className="msg-row ai">
              <div
                className="msg ai-msg fade-up"
                style={{ borderColor: draftTheme.color, background: draftTheme.soft }}
              >
                <div className="ai-bar" style={{ background: draftTheme.color }} />
                <div className="ai-content">{draft}</div>
              </div>
            </div>
          )}

          {isStreaming && !draft && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </div>

      <QuickEmotionPicker onPick={quickCheckin} />
      <InputBar
        value={input}
        onChange={setInput}
        onSend={send}
        disabled={isStreaming || !sessionId}
      />
    </div>
  );
}
