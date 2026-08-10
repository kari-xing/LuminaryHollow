/** 加载骨架占位。 */
export default function Skeleton({ height = 16 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} />;
}
