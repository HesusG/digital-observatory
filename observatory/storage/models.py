from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional


ItemKind = Literal["opportunity", "article"]


class CollectedItem(BaseModel):
    url: str
    title: str
    source: str
    source_type: str  # rss | wordpress | playwright
    raw_text: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    # opportunity = jobs/grants/scholarships/CFPs (existing radar)
    # article = AI/edtech news + research the user might post about
    kind: ItemKind = "opportunity"
    # finer-grained source group: opportunities | ai_news | ai_research | llm_tools | edtech
    source_group: str = "opportunities"
    # ISO-639-1 hint for the article's original language; the evaluator decides
    # which audiences (es / en) should actually see it
    lang_hint: str = "en"
    metadata: dict = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    affinity_score: int = 0
    is_free_or_funded: bool = False
    category: str = "general"
    summary: str = ""
    reasoning: str = ""


class EvaluatedItem(BaseModel):
    url: str
    title: str
    source: str
    source_type: str
    raw_text: str
    collected_at: datetime
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    evaluation: Optional[EvaluationResult] = None

    topics: list[str] = Field(default_factory=list)
    sentiment: str = "neutral"
    affinity_score: int = 0
    is_free_or_funded: bool = False
    category: str = "general"
    summary: str = ""
    reasoning: str = ""

    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    obsidian_path: Optional[str] = None
