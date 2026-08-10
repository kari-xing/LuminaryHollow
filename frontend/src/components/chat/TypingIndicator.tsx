/** “对方正在输入…”指示器（三点动画）。 */
export default function TypingIndicator() {
  return (
    <div className="msg-row ai">
      <div className="msg ai-msg typing-indicator">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}
