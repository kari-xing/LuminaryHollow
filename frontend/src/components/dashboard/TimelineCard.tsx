/** 每日摘要时间轴卡片。 */
export default function TimelineCard({
  items,
}: {
  items: { date: string; summary?: string | null; emotion_label?: string | null }[];
}) {
  if (!items.length) {
    return <div className="empty-state">还没有摘要，去聊聊天吧 🕯️</div>;
  }
  return (
    <div className="timeline">
      {items.map((item, i) => (
        <div className="timeline-item" key={i}>
          <div className="timeline-dot" />
          <div className="timeline-body">
            <div className="timeline-date">{item.date}</div>
            <div className="timeline-summary">{item.summary ?? '聊了一些心里话'}</div>
            {item.emotion_label && <span className="timeline-emotion">{item.emotion_label}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
