"""WebSocket 消息协议常量（与前端 ws/manager.ts 对齐）。"""

# 客户端 → 服务端
TYPE_USER_MESSAGE = "user_message"
TYPE_QUICK_CHECKIN = "quick_checkin"

# 服务端 → 客户端
TYPE_TYPING = "typing"
TYPE_STREAM_CHUNK = "stream_chunk"
TYPE_STREAM_END = "stream_end"
TYPE_QUICK_OK = "quick_ok"
TYPE_ERROR = "error"
TYPE_PING = "ping"

# 错误码（见需求文档 §10.7）
ERROR_LLM_UNAVAILABLE = 5001
ERROR_WS_AUTH = 4010
