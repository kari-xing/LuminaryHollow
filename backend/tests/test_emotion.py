"""情绪解析单元测试（覆盖规则识别 / 否定处理 / 强度 / emoji / 标签变体）。"""
from app.services.emotion import detect_emotion, parse_emotion_from_reply


def test_parse_reply_tag():
    result = parse_emotion_from_reply("别担心，一切都会好起来的。【情绪标签：焦虑】")
    assert result.label == "焦虑"
    assert result.score == 0.25


def test_parse_reply_tag_variant():
    # 兼容「情绪：低落」等变体与缺失右括号
    assert parse_emotion_from_reply("抱抱你【情绪：低落】").label == "低落"
    assert parse_emotion_from_reply("太棒了 情绪标签：开心").label == "开心"


def test_parse_reply_no_tag_fallback():
    result = parse_emotion_from_reply("抱抱你，很难过就哭出来吧")
    assert result.label in ("低落", "平静")


def test_detect_angry():
    result = detect_emotion("我真的气死了！")
    assert result.label == "愤怒"
    assert result.intensity >= 0.5


def test_detect_anxious_intensity():
    high = detect_emotion("明天面试，我超级焦虑，紧张得睡不着觉！！")
    low = detect_emotion("我有点担心明天的面试")
    assert high.label == "焦虑"
    assert low.label == "焦虑"
    assert high.intensity > low.intensity  # 程度副词应放大强度


def test_detect_negation():
    # 否定词不应误判
    assert detect_emotion("我不紧张，已经准备好了").label == "平静"
    assert detect_emotion("一点都不难过").label == "平静"


def test_detect_emoji():
    assert detect_emotion("今天太棒了😊🎉").label == "开心"
    assert detect_emotion("我真的要被气死了😡").label == "愤怒"


def test_detect_low():
    result = detect_emotion("最近好累，感觉撑不住了，想哭")
    assert result.label == "低落"


def test_detect_calm_default():
    result = detect_emotion("今天天气不错")
    assert result.label == "平静"
    assert result.intensity == 0.2

