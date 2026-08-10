import { useEffect, useState } from 'react';
import client from '../api/client';
import { formatDateTime } from '../utils/format';

interface MemoryItem {
  id: string;
  summary: string;
  memory_type: string;
  created_at: string;
}

const TYPE_LABEL: Record<string, string> = {
  event: '事件',
  emotion: '情绪',
  preference: '偏好',
};

export default function Memories() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await client.get('/memories', { params: { page: 1, page_size: 50 } });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const remove = async (id: string) => {
    await client.delete(`/memories/${id}`);
    load();
  };

  const clearAll = async () => {
    if (!confirm('确定清空全部长期记忆吗？此操作不可恢复。')) return;
    await client.delete('/memories');
    load();
  };

  return (
    <div className="memories-page">
      <h2 className="page-title">🧠 长期记忆</h2>
      <p className="page-sub">AI 记得你说过的话 —— 共 {total} 条，可随时删除</p>

      <div className="card">
        <div className="card-title">
          记忆列表
          {items.length > 0 && (
            <button className="btn btn-ghost danger" onClick={clearAll}>
              清空全部
            </button>
          )}
        </div>

        {loading && <div className="empty-state">加载中…</div>}

        {!loading && items.length === 0 && (
          <div className="empty-state">
            🕯️ 还没有长期记忆。多聊几轮后，AI 会自动帮你沉淀重要的内容。
          </div>
        )}

        <div className="memory-list">
          {items.map((m) => (
            <div className="memory-item" key={m.id}>
              <div className="memory-body">
                <div className="memory-summary">{m.summary}</div>
                <div className="memory-meta">
                  <span className="type-badge">{TYPE_LABEL[m.memory_type] ?? m.memory_type}</span>
                  <span>{formatDateTime(m.created_at)}</span>
                </div>
              </div>
              <button className="btn btn-ghost danger" onClick={() => remove(m.id)}>
                删除
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
