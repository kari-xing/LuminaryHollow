"""看板相关 Schema。"""
from datetime import date

from pydantic import BaseModel


class HeatmapDay(BaseModel):
    date: date
    avg_score: float | None = None
    count: int = 0
    label_mode: str | None = None


class HeatmapOut(BaseModel):
    year: int
    days: list[HeatmapDay]


class TrendPoint(BaseModel):
    date: date
    avg_score: float | None = None


class TrendOut(BaseModel):
    days: int
    points: list[TrendPoint]


class TimelineItem(BaseModel):
    session_id: str
    date: date
    duration_min: int
    summary: str | None = None
    emotion_label: str | None = None


class WordItem(BaseModel):
    text: str
    weight: int


class WordCloudOut(BaseModel):
    period: str
    words: list[WordItem]
