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
    if (this.ws && this.sessionId === sessionId) return;
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
        const msg = JSON.parse(ev.data) as WSMessage;
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
