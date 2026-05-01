from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CollectedItem(BaseModel):
    url: str
    title: str
    source: str
    source_type: str  # rss | scraper | changedetection | gmail
    raw_text: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class EvaluatedItem(BaseModel):
    url: str
    title: str
    source: str
    source_type: str
    raw_text: str
    collected_at: datetime
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    embedding: Optional[list[float]] = None
    topics: list[str] = Field(default_factory=list)
    sentiment: str = "neutral"
    affinity_score: int = 0
    is_free_or_funded: bool = False
    summary: str = ""
    reasoning: str = ""

    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    obsidian_path: Optional[str] = None
