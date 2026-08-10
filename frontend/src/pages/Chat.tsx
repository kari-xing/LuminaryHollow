import { useEffect, useMemo, useRef, useState } from 'react';
import client from '../api/client';
import { useAuthStore } from '../store/auth';
import { useChatStore, type ChatMessage } from '../store/chat';
import { wsManager } from '../ws/manager';
import MessageBubble, { QuickEmotionPicker } from '../components/chat/MessageBubble';
import InputBar from '../components/chat/InputBar';
import TypingIndicator from '../components/chat/TypingIndicator';
import { emotionByLabel } from '../theme/emotion';
import { AI_EMOJI, AI_NAME, greetingByHour, REMINDER_MESSAGES, REMINDER_EVERY_ROUNDS, REMINDER_LAST_ROUND_KEY, PLAN_PATTERN, workBuddyText, WORKBUDDY_EVERY_ROUNDS } from '../theme/companion';
import ReminderCard from '../components/chat/ReminderCard';
import ScheduleTimeConfirm from '../components/chat/ScheduleTimeConfirm';
import { useScheduleStore } from '../store/schedule';
import { extractDuePlans, QUESTION_HINTS } from '../utils/plan';
import { formatDate, formatTime } from '../utils/format';

/** 提醒卡片：聊到阈值冒出，打卡后留在本次会话的消息流历史。 */
interface ReminderItem {
  key: number; // 阈值序号（唯一，第 8 轮=0、16 轮=1…）
  idx: number; // 文案索引
  icon: string;
  text: string;
  createdAt: number; // 时间戳，用于并入消息流排序
  done: boolean;
}

/** WorkBuddy：从用户消息识别的计划提醒卡片。 */
interface WorkBuddyItem {
  key: number; // 唯一（Date.now()）
  plan: string;
  createdAt: number;
  done: boolean;
}

/** 对话自动补充日程后的提示卡片；scheduleId 存在时表示需要用户确认具体时间。 */
interface ScheduleHintItem {
  key: number;
  text: string;
  createdAt: number;
  scheduleId?: string;
  dueAt?: string;
  confirmed?: boolean;
}

/** 到点日程提醒卡片。 */
interface ScheduleAlarmItem {
  key: string; // 日程 id
  content: string;
  createdAt: number;
  done: boolean;
}

/** 从用户消息中提取「要去干什么」的计划（正则 MVP，去重保序；疑问句不提取）。 */
function extractPlans(content: string): string[] {
  const plans: string[] = [];
  PLAN_PATTERN.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = PLAN_PATTERN.exec(content)) !== null) {
    const p = (m[1] || '').trim();
    // 排除疑问句（「下午要干什么」）与过短内容
    if (p.length >= 2 && !QUESTION_HINTS.test(p) && !plans.includes(p)) plans.push(p);
  }
  return plans;
}

/** 读取最近已触发提醒的轮次（刷新后从下一个阈值继续冒卡，历史卡片不重现）。 */
function loadLastShownRound(): number {
  try {
    const v = Number(localStorage.getItem(REMINDER_LAST_ROUND_KEY) ?? 0);
    return Number.isFinite(v) && v >= 0 ? v : 0;
  } catch {
    return 0;
  }
}

/** 消息流渲染项：普通消息 / 贴心提醒 / WorkBuddy / 日程提示 / 到点提醒，按时间排序。 */
type TimelineEntry =
  | { type: 'message'; m: ChatMessage; at: number }
  | { type: 'reminder'; item: ReminderItem; at: number }
  | { type: 'workbuddy'; item: WorkBuddyItem; at: number }
  | { type: 'schedule-hint'; item: ScheduleHintItem; at: number }
  | { type: 'schedule-alarm'; item: ScheduleAlarmItem; at: number };

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
  // 防止 StrictMode 双执行 effect 时重复发起“创建会话”请求
  const initInFlight = useRef(false);
  // 最近已触发提醒的轮次（刷新后不重冒历史卡片，从下一个阈值继续）
  const lastShownRoundRef = useRef<number>(loadLastShownRound());
  // 提醒卡片：仅本次会话内存状态，打卡后留在消息流历史；刷新后不恢复
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  // WorkBuddy：聊天中识别到的计划与已冒出的提醒卡片
  const [plans, setPlans] = useState<string[]>([]);
  const [workBuddyItems, setWorkBuddyItems] = useState<WorkBuddyItem[]>([]);
  const workBuddyShown = useRef<Set<string>>(new Set()); // 已提醒过的计划（防重复）
  const workBuddyDone = useRef<Set<string>>(new Set()); // 已完成的计划
  const lastWorkBuddyRound = useRef(0);
  // 日程：对话自动补充的提示卡片 + 到点提醒卡片
  const [scheduleHints, setScheduleHints] = useState<ScheduleHintItem[]>([]);
  const [scheduleAlarms, setScheduleAlarms] = useState<ScheduleAlarmItem[]>([]);
  const alarmShown = useRef<Set<string>>(new Set());

  // 1. 初始化会话（不存在则创建）
  useEffect(() => {
    if (!token) return;
    (async () => {
      if (sessionId) {
        // 切换/刷新时加载历史消息
        const { data } = await client.get(`/sessions/${sessionId}`);
        useChatStore.getState().loadMessages(data.messages);
        return;
      }
      // 无会话：创建（同一时刻只允许一次，避免 StrictMode/HMR 下创建多个空会话）
      if (initInFlight.current) return;
      initInFlight.current = true;
      try {
        const { data } = await client.post('/sessions');
        useChatStore.getState().setSession(data.id);
      } finally {
        initInFlight.current = false;
      }
    })();
  }, [sessionId, token]);

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
            msg.emotion_label
              ? {
                  label: msg.emotion_label,
                  score: msg.emotion_score ?? 0.5,
                  intensity: msg.emotion_intensity ?? 0.5,
                }
              : undefined,
          );
          break;
        case 'quick_ok':
          break;
        case 'error':
          chat.endStream();
          break;
      }
    });
    return () => {
      unsub();
      // 离开聊天页：复位可能残留的流式状态（离开期间错过 stream_end 导致 isStreaming 卡住），
      // 避免返回后输入框被禁用、聊天区停在"回复中"
      useChatStore.setState({
        isStreaming: false,
        isTyping: false,
        draftContent: '',
        draftEmotion: null,
      });
    };
  }, [sessionId, token]);

  // 3. 自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, draft, reminders.length, workBuddyItems.length, scheduleHints.length, scheduleAlarms.length]);

  // 4. 长对话温馨提醒：每 N 轮真实对话（非快捷打卡）冒出一张卡片；
  //    从最近已触发的轮次继续，刷新后不会重冒历史卡片
  const userRoundCount = messages.filter((m) => m.role === 'user' && !m.is_quick_checkin).length;
  useEffect(() => {
    let next = lastShownRoundRef.current + REMINDER_EVERY_ROUNDS;
    while (userRoundCount >= next) {
      const i = next / REMINDER_EVERY_ROUNDS - 1;
      const tpl = REMINDER_MESSAGES[i % REMINDER_MESSAGES.length];
      setReminders((r) => [
        ...r,
        {
          key: i,
          idx: i % REMINDER_MESSAGES.length,
          icon: tpl.icon,
          text: tpl.text,
          createdAt: Date.now(),
          done: false,
        },
      ]);
      next += REMINDER_EVERY_ROUNDS;
    }
    if (next - REMINDER_EVERY_ROUNDS > lastShownRoundRef.current) {
      lastShownRoundRef.current = next - REMINDER_EVERY_ROUNDS;
      try {
        localStorage.setItem(REMINDER_LAST_ROUND_KEY, String(lastShownRoundRef.current));
      } catch {
        /* 忽略存储异常 */
      }
    }
  }, [userRoundCount]);

  // 5. WorkBuddy：每 N 轮真实对话，提醒一条之前提到的计划
  useEffect(() => {
    if (!userRoundCount || userRoundCount % WORKBUDDY_EVERY_ROUNDS !== 0) return;
    if (lastWorkBuddyRound.current === userRoundCount) return;
    const pending = plans.find(
      (p) =>
        !workBuddyShown.current.has(p) &&
        !workBuddyDone.current.has(p) &&
        !workBuddyItems.some((w) => w.plan === p),
    );
    if (!pending) return;
    lastWorkBuddyRound.current = userRoundCount;
    workBuddyShown.current.add(pending);
    setWorkBuddyItems((items) => [
      ...items,
      { key: Date.now(), plan: pending, createdAt: Date.now(), done: false },
    ]);
  }, [userRoundCount, plans, workBuddyItems]);

  /** WorkBuddy 打卡：留在消息流历史，不再重复提醒该计划。 */
  const checkWorkBuddy = (key: number, plan: string) => {
    workBuddyDone.current.add(plan);
    setWorkBuddyItems((items) => items.map((w) => (w.key === key ? { ...w, done: true } : w)));
  };

  // 6. 到点提醒：每分钟检查今日日程，5 分钟内到期且未完成 → 冒出提醒卡片
  useEffect(() => {
    const check = async () => {
      const today = formatDate(new Date().toISOString());
      try {
        const { data } = await client.get('/schedule', { params: { date: today } });
        const now = Date.now();
        for (const it of data.items) {
          if (it.done) continue;
          const due = new Date(it.due_at).getTime();
          if (due > now && due - now <= 5 * 60 * 1000 && !alarmShown.current.has(it.id)) {
            alarmShown.current.add(it.id);
            setScheduleAlarms((a) => [
              ...a,
              { key: it.id, content: it.content, createdAt: now, done: false },
            ]);
          }
        }
      } catch {
        /* 忽略轮询失败 */
      }
    };
    check();
    const timer = setInterval(check, 60_000);
    return () => clearInterval(timer);
  }, []);

  /** 到点提醒打卡：标记日程完成。 */
  const checkAlarm = (key: string) => {
    setScheduleAlarms((a) => a.map((x) => (x.key === key ? { ...x, done: true } : x)));
    useScheduleStore.getState().toggle(key, true);
  };

  /** 对话反问卡片确认时间：更新日程到期时间并刷新提示。 */
  const confirmScheduleTime = (key: number, scheduleId: string, dueAt: string, timeStr: string) => {
    const dateStr = formatDate(dueAt);
    const nextDue = new Date(`${dateStr}T${timeStr}:00`).toISOString();
    useScheduleStore.getState().updateDue(scheduleId, nextDue);
    setScheduleHints((h) =>
      h.map((x) => (x.key === key ? { ...x, confirmed: true, dueAt: nextDue } : x)),
    );
  };

  const greeting = greetingByHour(new Date().getHours()).text;

  /** 提醒打卡：卡片保留在本次会话的消息流历史中（仅前端状态，不持久化恢复）。 */
  const checkReminder = (key: number) => {
    setReminders((r) => r.map((item) => (item.key === key ? { ...item, done: true } : item)));
  };

  // 消息流：历史消息与提醒卡片按时间合并排序，打卡完成的卡片随对话自然上移
  const timeline = useMemo<TimelineEntry[]>(() => {
    const entries: TimelineEntry[] = [
      ...messages.map((m) => ({ type: 'message' as const, m, at: new Date(m.created_at).getTime() })),
      ...reminders.map((item) => ({ type: 'reminder' as const, item, at: item.createdAt })),
      ...workBuddyItems.map((item) => ({ type: 'workbuddy' as const, item, at: item.createdAt })),
      ...scheduleHints.map((item) => ({ type: 'schedule-hint' as const, item, at: item.createdAt })),
      ...scheduleAlarms.map((item) => ({ type: 'schedule-alarm' as const, item, at: item.createdAt })),
    ];
    entries.sort((a, b) => a.at - b.at);
    return entries;
  }, [messages, reminders, workBuddyItems, scheduleHints, scheduleAlarms]);

  const send = () => {
    const content = input.trim();
    // 同步读取 store：闭包里的 isStreaming 在重渲染前仍是旧值，
    // 直接用它判断会让连击/双击 Enter 重复发送同一条消息。
    if (!content || useChatStore.getState().isStreaming) return;
    setInput('');
    // WorkBuddy：识别用户提到的计划（"我下午要开会"等）
    const found = extractPlans(content);
    if (found.length) setPlans((p) => [...new Set([...p, ...found])]);
    // 日程：识别带时间的计划 → 自动加入日程并提示；没明确几点 → 反问用户
    const duePlans = extractDuePlans(content);
    if (duePlans.length) {
      duePlans.forEach((p) => {
        useScheduleStore
          .getState()
          .add(p.content, p.dueAt, 'chat')
          .then((created) => {
            if (!created) return;
            if (p.timeGuess) {
              setScheduleHints((h) => [
                ...h,
                {
                  key: Date.now() + Math.random(),
                  text: `小光：好的，「${p.content}」我记下啦，暂定 ${formatTime(p.dueAt)}。你想几点开始呀？`,
                  createdAt: Date.now(),
                  scheduleId: created.id,
                  dueAt: p.dueAt,
                  confirmed: false,
                },
              ]);
            } else {
              setScheduleHints((h) => [
                ...h,
                {
                  key: Date.now() + Math.random(),
                  text: `已把「${p.content}」加入日程 📅（${formatDate(p.dueAt)} ${formatTime(p.dueAt)}）`,
                  createdAt: Date.now(),
                },
              ]);
            }
          });
      });
    }
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
              <div className="msg-row ai greeting-row">
                <div className="msg-avatar ai">{AI_EMOJI}</div>
                <div className="msg greeting-msg">
                  <div className="ai-bar" style={{ background: '#90A4AE' }} />
                  <div className="ai-meta">
                    <span className="ai-name">{AI_NAME}</span>
                    <span className="online-dot" />
                    <span className="msg-time">在线</span>
                  </div>
                  <div className="ai-content">{greeting}</div>
                </div>
              </div>
              <p className="chat-empty-sub">把心事说出来，我会认真记住、好好陪着你。</p>
            </div>
          )}

          {timeline.map((entry) => {
            if (entry.type === 'message') {
              return (
                <MessageBubble
                  key={entry.m.id}
                  role={entry.m.role}
                  content={entry.m.content}
                  emotionLabel={entry.m.emotion_label}
                  emotionIntensity={entry.m.emotion_intensity}
                  isPrivate={entry.m.is_quick_checkin ? false : undefined}
                  isQuickCheckin={entry.m.is_quick_checkin}
                  time={entry.m.created_at}
                />
              );
            }
            if (entry.type === 'workbuddy') {
              return (
                <div key={`workbuddy-${entry.item.key}`} className="msg-row ai fade-up">
                  <div className="msg-avatar ai">{AI_EMOJI}</div>
                  <ReminderCard
                    icon="📌"
                    title={`${AI_NAME} · WorkBuddy`}
                    text={workBuddyText(entry.item.plan)}
                    done={entry.item.done}
                    onCheck={() => checkWorkBuddy(entry.item.key, entry.item.plan)}
                  />
                </div>
              );
            }
            if (entry.type === 'schedule-hint') {
              return (
                <div key={`sched-hint-${entry.item.key}`} className="msg-row ai fade-up">
                  <div className="msg-avatar ai">{AI_EMOJI}</div>
                  <div className="msg schedule-hint-msg">
                    <div className="ai-bar" style={{ background: '#4CAF50' }} />
                    {entry.item.scheduleId && !entry.item.confirmed ? (
                      <ScheduleTimeConfirm
                        text={entry.item.text}
                        dueAt={entry.item.dueAt!}
                        confirmed={entry.item.confirmed ?? false}
                        onConfirm={(t) =>
                          confirmScheduleTime(
                            entry.item.key,
                            entry.item.scheduleId!,
                            entry.item.dueAt!,
                            t,
                          )
                        }
                        onDismiss={() =>
                          setScheduleHints((h) => h.filter((x) => x.key !== entry.item.key))
                        }
                      />
                    ) : (
                      <div className="ai-content">{entry.item.text}</div>
                    )}
                  </div>
                </div>
              );
            }
            if (entry.type === 'schedule-alarm') {
              return (
                <div key={`alarm-${entry.item.key}`} className="msg-row ai fade-up">
                  <div className="msg-avatar ai">{AI_EMOJI}</div>
                  <ReminderCard
                    icon="⏰"
                    title={`${AI_NAME} · 日程提醒`}
                    text={`该去「${entry.item.content}」啦`}
                    done={entry.item.done}
                    onCheck={() => checkAlarm(entry.item.key)}
                  />
                </div>
              );
            }
            return (
              <div key={`reminder-${entry.item.key}`} className="msg-row ai fade-up">
                <div className="msg-avatar ai">{AI_EMOJI}</div>
                <ReminderCard
                  icon={entry.item.icon}
                  text={entry.item.text}
                  done={entry.item.done}
                  onCheck={() => checkReminder(entry.item.key)}
                />
              </div>
            );
          })}

          {showDraft && (
            <div className="msg-row ai fade-up">
              <div className="msg-avatar ai">🕯️</div>
              <div className="msg" style={{ borderColor: draftTheme.color }}>
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
