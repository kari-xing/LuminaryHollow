"""情绪感知：规则识别 + 强度计算 + LLM 标签解析。

升级说明：
- 扩充关键词库，优先使用短语减少误伤
- 否定词处理：情绪词前出现"不/没/没有"等时忽略该命中（"我不紧张"不会误判焦虑）
- 强度分级：程度副词（非常/有点）+ 感叹号 + emoji 综合计算 intensity(0~1)
- emoji 直接映射情绪
"""

import re
from dataclasses import dataclass

# 情绪 → 基础积极程度（0~1，0 消极 / 1 积极）
EMOTION_SCORE: dict[str, float] = {
    "开心": 0.85,
    "平静": 0.60,
    "低落": 0.35,
    "焦虑": 0.25,
    "愤怒": 0.10,
}

EMOTION_LABELS = set(EMOTION_SCORE)

# 程度副词 → 强度增量
_HIGH_INTENSIFIERS = (
    "超级", "极其", "万分", "格外", "极度", "非常非常", "特别特别",
    "非常", "特别", "十分", "相当", "狠狠", "彻底", "太",
)
_LOW_INTENSIFIERS = ("有点", "有些", "稍微", "一点点", "些许", "略", "微微", "一丝", "不太")

# 否定词：情绪词前出现则忽略该命中
_NEGATIONS = ("不", "没", "没有", "别", "并非", "不是", "不会", "不用", "毫无", "无")
_NEGATION_WINDOW = 3

# 表情符号 → 情绪
_EMOJI_MAP: dict[str, str] = {
    "😊": "开心", "😄": "开心", "😂": "开心", "🤣": "开心", "🤗": "开心", "🥳": "开心",
    "😢": "低落", "😭": "低落", "😞": "低落", "💔": "低落", "🥺": "低落",
    "😡": "愤怒", "🤬": "愤怒", "💢": "愤怒",
    "😰": "焦虑", "😨": "焦虑", "😱": "焦虑", "😵": "焦虑", "😖": "焦虑",
}

# 关键词库：优先长短语，减少单字误伤
_KEYWORDS: dict[str, list[str]] = {
    "开心": [
        "太好了", "太棒了", "开心", "高兴", "好开心", "真开心", "兴奋", "快乐", "幸福",
        "成功上岸", "通过了", "录取", "中奖", "哈哈", "笑死我了", "超棒", "真不错", "不错不错", "好耶",
    ],
    "愤怒": [
        "气死我了", "气死了", "气炸", "太生气了", "很生气", "生气", "愤怒", "可恶", "太过分",
        "过分", "太气人", "气人", "恼火", "火大", "烦死了", "忍不了", "太讨厌", "讨厌",
        "凭什么", "无语死了", "搞不懂", "气到发抖", "恶心", "欺人太甚",
    ],
    "焦虑": [
        "焦虑", "紧张", "担心", "害怕", "压力好大", "压力大", "压力", "好慌", "慌", "失眠",
        "睡不着", "怎么办", "好烦", "纠结", "不安", "担忧", "怕", "睡不着觉", "崩溃",
        "面试", "考试", "裁员", "deadline", "ddl", "论文", "答辩", "来不及", "赶不上了",
    ],
    "低落": [
        "难过", "伤心", "好难过", "低落", "沮丧", "失望", "想哭", "哭了", "哭", "孤独",
        "寂寞", "好累", "累了", "没意思", "emo", "崩溃", "没劲", "委屈", "迷茫", "难受",
        "失落", "自卑", "撑不住", "坚持不下去", "心累", "无助",
        "不开心", "不高兴", "不快乐", "郁闷", "没心情", "提不起劲", "高兴不起来", "麻木", "烦得很",
        "被骂", "挨骂", "被批评", "被吼", "被训", "被数落", "被说", "被打击",
        "批评", "被批", "挨批", "指责", "被指责", "训斥",
    ],
    "平静": [
        "还好", "平静", "淡定", "还行", "没事", "放松", "顺其自然", "就这样吧", "可以接受", "无所谓", "挺好",
    ],
}

_TAG_RE = re.compile(
    r"(?:【\s*(?:情绪标签|情绪)\s*[:：]?\s*|(?:情绪标签|情绪)\s*[:：]\s*)"
    r"(?P<label>[^】\]\n]{1,12})[】\s，,。.!！]*"
)

# 模型可能输出的近似标签 → 白名单映射
_TAG_ALIASES: dict[str, str] = {
    "疲惫": "低落", "无助": "低落", "失望": "低落", "伤心": "低落", "委屈": "低落",
    "难过": "低落", "沮丧": "低落", "孤独": "低落", "迷茫": "低落", "累了": "低落",
    "紧张": "焦虑", "担忧": "焦虑", "不安": "焦虑", "着急": "焦虑", "担心": "焦虑",
    "惶恐": "焦虑", "慌乱": "焦虑", "有压力": "焦虑", "压力大": "焦虑",
    "生气": "愤怒", "烦躁": "愤怒", "恼火": "愤怒", "火大": "愤怒", "不满": "愤怒",
    "气愤": "愤怒", "讨厌": "愤怒",
    "高兴": "开心", "快乐": "开心", "兴奋": "开心", "幸福": "开心", "喜悦": "开心",
    "自豪": "开心", "期待": "开心", "惊喜": "开心",
    "淡定": "平静", "从容": "平静", "放松": "平静", "安宁": "平静",
    "不开心": "低落", "不高兴": "低落", "不快乐": "低落", "郁闷": "低落", "委屈": "低落",
}

# 用于从回复正文中剥离情绪标签（只解析、不展示）
_TAG_CLEAN_RE = re.compile(
    r"[【\[]\s*(?:情绪标签|情绪)\s*[:：]?\s*[^】\]\n]{0,12}[】\]]"
)


def strip_emotion_tag(text: str) -> str:
    """移除回复正文中的【情绪标签：xxx】标记，避免展示给用户。"""
    return _TAG_CLEAN_RE.sub("", text).strip()


@dataclass
class EmotionResult:
    label: str
    score: float
    intensity: float = 0.5


# 否定词 + 正面情绪词（如"不开心""高兴不起来"）→ 反向映射为低落
_NEGATED_POSITIVE = (
    "开心", "高兴", "快乐", "幸福", "兴奋", "愉快", "舒服", "满意", "好受", "轻松", "自在",
)


def _is_negated(text: str, pos: int) -> bool:
    """情绪词命中位置前 _NEGATION_WINDOW 字符内出现否定词则视为被否定。"""
    start = max(0, pos - _NEGATION_WINDOW)
    segment = text[start:pos]
    return any(neg in segment for neg in _NEGATIONS)


def _count_negated_positives(text: str) -> int:
    """否定词 + 正面情绪词（如"我都不开心"）→ 视为消极（低落）。"""
    count = 0
    for w in _NEGATED_POSITIVE:
        idx = 0
        while True:
            pos = text.find(w, idx)
            if pos == -1:
                break
            if _is_negated(text, pos):
                count += 1
            idx = pos + len(w)
    return count


def _calc_intensity(text: str, label: str) -> float:
    """综合程度副词 / 感叹号 / emoji / 句长计算情绪强度（0~1）。"""
    if label == "平静":
        return 0.2
    base = 0.5
    for w in _HIGH_INTENSIFIERS:
        if w in text:
            base += 0.25
            break
    for w in _LOW_INTENSIFIERS:
        if w in text:
            base -= 0.2
            break
    base += min(0.3, text.count("！") * 0.1 + text.count("!") * 0.08)
    if any(e in text for e in ("😭", "😡", "😰", "😱", "🥺", "💢")):
        base += 0.2
    if len(text) <= 6:
        base += 0.1  # 简短强烈的表达
    return max(0.2, min(1.0, round(base, 2)))


def detect_emotion(text: str) -> EmotionResult:
    """规则识别：关键词（否定感知）+ emoji 计数 → 综合评分取最优。"""
    hits: dict[str, int] = {}
    for label, words in _KEYWORDS.items():
        count = 0
        for word in words:
            idx = 0
            while True:
                pos = text.find(word, idx)
                if pos == -1:
                    break
                if not _is_negated(text, pos):
                    count += 1
                idx = pos + len(word)
        if count:
            hits[label] = hits.get(label, 0) + count

    for emoji, label in _EMOJI_MAP.items():
        if emoji in text:
            hits[label] = hits.get(label, 0) + 1

    # 否定词 + 正面情绪词（"我都不开心""高兴不起来"）→ 低落
    negated = _count_negated_positives(text)
    if negated:
        hits["低落"] = hits.get("低落", 0) + negated

    if not hits:
        return EmotionResult("平静", EMOTION_SCORE["平静"], 0.2)

    # 消极情绪优先级更高，避免"开心"与"担心"并存时误判
    priority = {"愤怒": 5, "焦虑": 4, "低落": 3, "开心": 2, "平静": 1}
    label = max(hits, key=lambda k: (hits[k] * priority[k], priority[k]))
    return EmotionResult(label, EMOTION_SCORE[label], _calc_intensity(text, label))


def parse_emotion_from_reply(reply: str) -> EmotionResult:
    """解析 LLM 回复尾部携带的情绪标签（白名单 + 近似别名映射）；失败则规则兜底。"""
    m = _TAG_RE.search(reply)
    if m:
        raw = m.group("label").strip()
        label = raw if raw in EMOTION_LABELS else _TAG_ALIASES.get(raw)
        if label:
            return EmotionResult(label, EMOTION_SCORE[label], 0.5)
    return detect_emotion(reply)

