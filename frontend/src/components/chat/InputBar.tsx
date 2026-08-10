/** 输入框：Enter 发送、Shift+Enter 换行；发送时禁用。 */
export default function InputBar({
  value,
  onChange,
  onSend,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled: boolean;
}) {
  return (
    <div className="input-area">
      <textarea
        className="input chat-input"
        placeholder="和树洞说说心里话吧…"
        value={value}
        rows={2}
        maxLength={2000}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (value.trim() && !disabled) onSend();
          }
        }}
      />
      <button className="btn send-btn" onClick={onSend} disabled={disabled || !value.trim()}>
        发送
      </button>
    </div>
  );
}
