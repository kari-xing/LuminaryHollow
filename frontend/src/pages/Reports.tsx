import { useEffect, useState } from 'react';
import client from '../api/client';

interface Report {
  id: string;
  week_start: string;
  week_end: string;
  summary: string;
  generated_at: string;
}

export default function Reports() {
  const [latest, setLatest] = useState<Report | null>(null);
  const [items, setItems] = useState<Report[]>([]);

  useEffect(() => {
    (async () => {
      const [l, list] = await Promise.all([
        client.get('/reports/weekly/latest'),
        client.get('/reports/weekly'),
      ]);
      setLatest(l.data.report);
      setItems(list.data.items);
    })();
  }, []);

  const reports = latest ? [latest, ...items.filter((i) => i.id !== latest.id)] : items;

  return (
    <div className="reports-page">
      <h2 className="page-title">📄 历史周报</h2>
      <p className="page-sub">每周日晚自动生成，回顾一周的情绪与焦点</p>

      {reports.length === 0 && (
        <div className="card">
          <div className="empty-state">还没有周报。每周日 22:00 会自动生成 🗓️</div>
        </div>
      )}

      <div className="report-list">
        {reports.map((r) => (
          <div className="card report-item" key={r.id}>
            <div className="report-head">
              <span className="report-period">
                {r.week_start} ~ {r.week_end}
              </span>
              <span className="report-created">{r.generated_at?.slice(0, 10)}</span>
            </div>
            <div className="report-summary">{r.summary}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
