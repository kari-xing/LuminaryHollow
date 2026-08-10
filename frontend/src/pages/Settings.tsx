import { useEffect, useState } from 'react';
import client from '../api/client';

interface Profile {
  name?: string | null;
  age?: number | null;
  occupation?: string | null;
  goal?: string | null;
  struggle?: string | null;
  preferred_tone?: string;
  privacy_mode?: boolean;
}

export default function Settings() {
  const [form, setForm] = useState<Profile>({});
  const [saved, setSaved] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    (async () => {
      const { data } = await client.get('/users/me/profile');
      setForm(data);
    })();
  }, []);

  const set = (key: keyof Profile, value: string | number | boolean) =>
    setForm((f) => ({ ...f, [key]: value }));

  const save = async () => {
    await client.put('/users/me/profile', form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const doExport = async () => {
    setExporting(true);
    try {
      const resp = await client.get('/export', { responseType: 'blob' });
      const url = URL.createObjectURL(resp.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'export.zip';
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="settings-page">
      <h2 className="page-title">⚙️ 用户设置</h2>
      <p className="page-sub">让我更了解你，才能更好地陪伴你（均可跳过）</p>

      <div className="card">
        <div className="card-title">基础画像</div>
        <div className="form-grid">
          <label>
            称呼
            <input className="input" value={form.name ?? ''} onChange={(e) => set('name', e.target.value)} placeholder="怎么称呼你？" />
          </label>
          <label>
            年龄
            <input
              className="input"
              type="number"
              value={form.age ?? ''}
              onChange={(e) => set('age', Number(e.target.value) || 0)}
              placeholder="0"
            />
          </label>
          <label>
            职业
            <input className="input" value={form.occupation ?? ''} onChange={(e) => set('occupation', e.target.value)} placeholder="如：产品经理" />
          </label>
        </div>
        <label>
          近期目标
          <textarea className="input" value={form.goal ?? ''} onChange={(e) => set('goal', e.target.value)} placeholder="最近最想达成的事…" rows={2} />
        </label>
        <label>
          长期困扰
          <textarea className="input" value={form.struggle ?? ''} onChange={(e) => set('struggle', e.target.value)} placeholder="一直让你纠结的事…" rows={2} />
        </label>
        <button className="btn" onClick={save}>
          {saved ? '✅ 已保存' : '保存画像'}
        </button>
      </div>

      <div className="card">
        <div className="card-title">隐私与数据</div>
        <div className="privacy-row">
          <div>
            <strong>隐私模式</strong>
            <div className="page-sub">开启后对话不会被写入长期记忆、不参与看板统计</div>
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={!!form.privacy_mode}
              onChange={(e) => set('privacy_mode', e.target.checked)}
            />
            <span className="slider" />
          </label>
        </div>
        <div className="privacy-row">
          <div>
            <strong>导出全部数据</strong>
            <div className="page-sub">下载对话记录（JSON / Markdown）与画像，归你所有</div>
          </div>
          <button className="btn btn-ghost" onClick={doExport} disabled={exporting}>
            {exporting ? '导出中…' : '导出'}
          </button>
        </div>
      </div>
    </div>
  );
}
