"""WebSocket 连接管理器与日程查询检测单元测试。

重点：同一会话重复连接时，新连接必须顶掉旧连接，确保 send_json 只广播一份，
避免前端收到重复的流式内容（旧 bug：新旧连接并存 → stream_chunk 广播两份）。
"""
import pytest

from app.ws.chat import _SCHEDULE_QUERY_RE
from app.ws.manager import ConnectionManager


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed = False

    async def accept(self) -> None:
        pass

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_connect_replaces_old_connection():
    """同一会话再次 connect 时，旧连接被关闭，消息只广播给最新连接一份。"""
    m = ConnectionManager()
    ws1, ws2 = FakeWS(), FakeWS()
    await m.connect("s1", ws1)
    await m.connect("s1", ws2)  # 新连接顶掉旧连接
    await m.send_json("s1", {"type": "stream_chunk", "content": "你"})
    assert ws1.closed is True  # 旧连接已被顶掉
    assert len(ws2.sent) == 1  # 只收一份，不重复
    assert ws2.sent[0]["content"] == "你"


@pytest.mark.asyncio
async def test_disconnect_keeps_other_sessions():
    m = ConnectionManager()
    ws1, ws2 = FakeWS(), FakeWS()
    await m.connect("s1", ws1)
    await m.connect("s2", ws2)
    await m.disconnect("s1", ws1)
    await m.send_json("s1", {"type": "ping"})
    await m.send_json("s2", {"type": "ping"})
    assert len(ws1.sent) == 0  # s1 已清理
    assert len(ws2.sent) == 1  # 不受影响


def test_schedule_query_regex_hits():
    assert _SCHEDULE_QUERY_RE.search("今天还有什么事没干")
    assert _SCHEDULE_QUERY_RE.search("今天还有什么安排")
    assert _SCHEDULE_QUERY_RE.search("我今天要干什么")
    assert _SCHEDULE_QUERY_RE.search("现在有什么日程吗")
    assert _SCHEDULE_QUERY_RE.search("今天有哪些事没做")
    # 直接问「今天的日程安排」也能识别
    assert _SCHEDULE_QUERY_RE.search("今天的日程安排")
    assert _SCHEDULE_QUERY_RE.search("今天有日程吗")
    assert _SCHEDULE_QUERY_RE.search("把今天的日程发我")


def test_schedule_query_regex_misses():
    # 计划陈述不是查询
    assert not _SCHEDULE_QUERY_RE.search("今天安排去爬山")
    # 没有「今天/现在/还有」时间限定，不算今日日程查询
    assert not _SCHEDULE_QUERY_RE.search("下午要干什么")
    assert not _SCHEDULE_QUERY_RE.search("晚上吃什么")
    # 状态描述
    assert not _SCHEDULE_QUERY_RE.search("今天天气不错")
