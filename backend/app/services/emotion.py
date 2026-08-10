"""情绪感知：识别 / 解析 / 评分 / 兜底。

标签白名单（枚举），解析策略：
1. 优先正则提取回复尾部【情绪标签：xxx】
2. 匹配失败时基于关键词规则兜底
3. 仍失败 → 默认「平静」
"""
import re
from dataclasses import dataclass

# 情绪 → 积极程度评分（0~1）
EMOTION_SCORE: dict[str, float] = {
    "开心": 0.85,
    "平静": 0.6,
    "低落": 0.35,
    "焦虑": 0.25,
    "愤怒": 0.1,
}

EMOTION_LABELS = set(EMOTION_SCORE.keys())

# 关键词 → 情绪（简单兜底规则）
_KEYWORDS: dict[str, list[str]] = {
    "开心": ["开心", "高兴", "太好了", "哈哈", "棒", "幸福", "兴奋", "快乐"],
    "愤怒": ["生气", "愤怒", "气死", "可恶", "恨", "气人", "恼火", "烦死"],
    "焦虑": ["焦虑", "紧张", "担心", "害怕", "压力", "慌", "失眠", "怎么办"],
    "低落": ["难过", "伤心", "低落", "沮丧", "失望", "哭", "孤独", "累", "没意思", "emo"],
}

_TAG_RE = re.compile(r"【\s*情绪标签\s*[:：]\s*(?P<label>[^】]+)\s*】")


@dataclass
class EmotionResult:
    label: str
    score: float


def parse_emotion_from_reply(reply: str) -> EmotionResult:
    """解析 LLM 回复尾部携带的情绪标签。"""
    m = _TAG_RE.search(reply)
    if m:
        label = m.group("label").strip()
        if label in EMOTION_LABELS:
            return EmotionResult(label, EMOTION_SCORE[label])
    # 兜底：关键词规则
    return detect_emotion(reply)


def detect_emotion(text: str) -> EmotionResult:
    """基于关键词规则识别用户情绪（Prompt 不可用时的降级方案）。"""
    for label, words in _KEYWORDS.items():
        if any(w in text for w in words):
            return EmotionResult(label, EMOTION_SCORE[label])
    return EmotionResult("平静", EMOTION_SCORE["平静"])
