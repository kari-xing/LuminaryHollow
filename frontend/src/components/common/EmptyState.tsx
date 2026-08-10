/** 空状态占位。 */
export default function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}
