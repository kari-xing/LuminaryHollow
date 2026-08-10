/**
 * WebSocket 管理器（单例）：连接 / 心跳 / 自动重连 / 消息路由。
 * 协议与后端 app/ws/protocol.py 对齐。
 */
export type WSHandler = (msg: WSMessage) => void;

export type WSMessage = {
  type: string;
  content?: string;
  emotion_label?: string;
  emotion_score?: number;
  emotion_intensity?: number;
  code?: number;
  message?: string;
  session_id?: string;
};

class WSManager {
  private ws: WebSocket | null = null;
  private handlers = new Set<WSHandler>();
  private heartbeatTimer?: ReturnType<typeof setInterval>;
  private reconnectTimer?: ReturnType<typeof setTimeout>;
  private retries = 0;
  private sessionId: string | null = null;
  private token: string | null = null;

  connect(sessionId: string, token: string) {
    // 关键修复：确保任意时刻只有一个 WebSocket 连接，且连接必须匹配当前 session 与 token。
    // 若旧连接属于不同 session，或 token 已变化（如 401 刷新），先彻底关闭（阻止自动重连），
    // 避免双连接各收一份消息 → 前端重复。
    if (this.ws && (this.sessionId !== sessionId || this.token !== token)) {
      this.ws.onclose = null;
      this.ws.onmessage = null;
      this.ws.close();
      this.ws = null;
      this.sessionId = null;
      this.token = null;
    }
    if (this.ws && this.sessionId === sessionId && this.token === token) {
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) return;
      this.ws = null; // 已关闭的连接直接重建
    }
    this.sessionId = sessionId;
    this.token = token;
    this.open();
  }

  private open() {
    const base = import.meta.env.VITE_WS_BASE || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
    this.ws = new WebSocket(`${base}/chat/${this.sessionId}?token=${this.token}`);

    this.ws.onopen = () => {
      this.retries = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (ev) => {
      try {
        // 只处理「当前生效的 socket」：极端情况下（旧 socket 尚未清理干净、或 HMR
        // 重建了 manager 实例），旧 socket 可能仍会收到消息。若 this.ws 已被替换，
        // 直接忽略旧 socket 的帧，避免同一份 stream_chunk 被追加两次 → 文字重复。
        // （ev.currentTarget 可能缺失于测试 mock，此时跳过该检查）
        if (ev.currentTarget != null && this.ws !== ev.currentTarget) return;
        const msg = JSON.parse(ev.data) as WSMessage;
        // 开发模式诊断：查看每条 WS 消息及当前 handler 数量（排查重复）
        if (import.meta.env.DEV) {
          console.debug('[ws]', msg.type, 'handlers=' + this.handlers.size, (msg.content || '').slice(0, 20));
        }
        this.handlers.forEach((h) => h(msg));
      } catch {
        /* 忽略非法帧 */
      }
    };

    this.ws.onclose = () => this.scheduleReconnect();
    this.ws.onerror = () => this.ws?.close();
  }

  private scheduleReconnect() {
    this.stopHeartbeat();
    // 指数退避重连，最多 5 次
    if (this.retries >= 5) return;
    const delay = Math.min(1000 * 2 ** this.retries, 15_000);
    this.retries += 1;
    this.reconnectTimer = setTimeout(() => this.open(), delay);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({ type: 'ping' }));
    }, 30_000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
  }

  send(payload: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }

  onMessage(handler: WSHandler): () => void {
    // 本项目仅需一个消费者。注册新 handler 前先清空所有旧 handler，
    // 保证任意时刻 handlers 集合中最多只有一个 handler。
    // 之前的 while(size >= 2) 逻辑存在漏洞：size 恰好为 1 时直接 add 会变成 2 个，
    // 多个 handler 会让同一条 stream_chunk 被追加多次 → 界面出现重复的字。
    this.handlers.clear();
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
  }
}

export const wsManager = new WSManager();
