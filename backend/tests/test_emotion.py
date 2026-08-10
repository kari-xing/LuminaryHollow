"""情绪解析单元测试。"""
from app.services.emotion import detect_emotion, parse_emotion_from_reply


def test_parse_reply_tag():
    result = parse_emotion_from_reply("别担心，一切都会好起来的。【情绪标签：焦虑】")
    assert result.label == "焦虑"
    assert result.score == 0.25


def test_parse_reply_no_tag_fallback():
    result = parse_emotion_from_reply("抱抱你，很难过就哭出来吧")
    assert result.label in ("低落", "平静")


def test_detect_angry():
    result = detect_emotion("我真的气死了！")
    assert result.label == "愤怒"


def test_detect_calm_default():
    result = detect_emotion("今天天气不错")
    assert result.label == "平静"
