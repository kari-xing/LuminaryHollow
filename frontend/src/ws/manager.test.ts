/**
 * WSManager 消息路由去重测试。
 *
 * 背景：历史 bug —— onMessage 使用 while(size >= 2) 清理旧 handler，
 * 在 size 恰好为 1 时直接 add 会导致集合里同时存在 2 个 handler，
 * 每一条 stream_chunk 被追加两次 → 前端出现「重复的话语」（日志正确）。
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { wsManager, type WSHandler, type WSMessage } from './manager';

/** 最小可用的 WebSocket 伪实现（node 环境没有浏览器 WebSocket）。 */
class MockWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];

  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string; currentTarget?: unknown }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closeCalled = 0;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
    // 模拟异步握手成功
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.();
    }, 0);
  }

  close() {
    this.closeCalled += 1;
    this.readyState = MockWebSocket.CLOSED;
  }

  send(_data: string) {
    /* 忽略 */
  }
}

const OriginalWebSocket = globalThis.WebSocket;

beforeEach(() => {
  MockWebSocket.instances = [];
  (globalThis as any).WebSocket = MockWebSocket;
  // manager.open() 依赖浏览器 location，node 环境下补一个最小 mock
  (globalThis as any).location = { protocol: 'http:', host: 'localhost:5173' };
  wsManager.disconnect();
});

afterEach(() => {
  wsManager.disconnect();
  if (OriginalWebSocket) {
    (globalThis as any).WebSocket = OriginalWebSocket;
  } else {
    delete (globalThis as any).WebSocket;
  }
  delete (globalThis as any).location;
});

/** 向当前活动连接投递一条服务端消息。 */
function dispatch(msg: WSMessage, target?: MockWebSocket) {
  const conn = target ?? MockWebSocket.instances[MockWebSocket.instances.length - 1];
  expect(conn, '应存在活动连接').toBeTruthy();
  conn!.onmessage?.({ data: JSON.stringify(msg), currentTarget: conn });
}

/** 等待连接握手完成。 */
async function waitOpen() {
  await new Promise((r) => setTimeout(r, 10));
}

describe('WSManager 消息去重', () => {
  it('重复注册 onMessage 时，只有最后一个 handler 生效', async () => {
    await waitOpen();
    wsManager.connect('s1', 'token1');

    const received: string[] = [];
    const h1: WSHandler = () => received.push('h1');
    const h2: WSHandler = () => received.push('h2');

    wsManager.onMessage(h1);
    wsManager.onMessage(h2); // 关键：第二次注册必须顶掉第一个

    dispatch({ type: 'stream_chunk', content: '你' });
    dispatch({ type: 'stream_chunk', content: '好' });

    // 修复前：h1、h2 各收到一次，received 为 ['h1','h2','h1','h2']
    expect(received).toEqual(['h2', 'h2']);
  });

  it('同一 stream_chunk 帧只会被消费一次，不会造成文字翻倍', async () => {
    await waitOpen();
    wsManager.connect('s1', 'token1');

    let chunkCount = 0;
    wsManager.onMessage((msg) => {
      if (msg.type === 'stream_chunk') chunkCount += 1;
    });

    dispatch({ type: 'stream_chunk', content: '哈' });
    dispatch({ type: 'stream_chunk', content: '哈' }); // 两个独立的合法帧

    expect(chunkCount).toBe(2);
  });

  it('onMessage 返回的取消函数可移除 handler', async () => {
    await waitOpen();
    wsManager.connect('s1', 'token1');

    let count = 0;
    const unsub = wsManager.onMessage(() => {
      count += 1;
    });
    unsub();
    dispatch({ type: 'stream_chunk', content: 'x' });
    expect(count).toBe(0);
  });

  it('token 变化时重建连接，避免陈旧连接与新连接并存', async () => {
    wsManager.connect('s1', 'tokenA');
    await waitOpen();
    const oldConn = MockWebSocket.instances[MockWebSocket.instances.length - 1]!;

    wsManager.connect('s1', 'tokenB'); // token 已变 → 应关闭旧连接并重建
    await waitOpen();

    expect(oldConn.closeCalled).toBe(1);
    expect(MockWebSocket.instances.length).toBe(2);
  });

  it('相同 session 与 token 重复 connect 时复用连接，不新建', async () => {
    wsManager.connect('s1', 'tokenA');
    await waitOpen();
    wsManager.connect('s1', 'tokenA');
    await waitOpen();
    expect(MockWebSocket.instances.length).toBe(1);
  });

  it('旧连接的消息被忽略，不会造成重复', async () => {
    wsManager.connect('s1', 'tokenA');
    await waitOpen();
    const oldConn = MockWebSocket.instances[MockWebSocket.instances.length - 1]!;

    wsManager.connect('s1', 'tokenB'); // 重建连接，this.ws 指向新连接
    await waitOpen();
    const newConn = MockWebSocket.instances[MockWebSocket.instances.length - 1]!;
    expect(newConn).not.toBe(oldConn);

    let count = 0;
    wsManager.onMessage((msg) => {
      if (msg.type === 'stream_chunk') count += 1;
    });

    // 模拟：陈旧连接的 onmessage 仍被触发（防御场景），应被 manager 忽略
    dispatch({ type: 'stream_chunk', content: '哈' }, oldConn);
    dispatch({ type: 'stream_chunk', content: '哈' }, newConn);
    expect(count).toBe(1);
  });
});
