from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


# ── Message schemas ────────────────────────────────────────────────────────────

class MessageBase(BaseModel):
    message_id: str
    channel_name: str
    message_date: datetime
    message_text: Optional[str] = None
    has_media: bool = False
    image_path: Optional[str] = None
    views: int = 0
    forwards: int = 0


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# ── Analytical response schemas ────────────────────────────────────────────────

class TopProductItem(BaseModel):
    term: str
    frequency: int


class TopProductsResponse(BaseModel):
    limit: int
    results: List[TopProductItem]


class DailyActivity(BaseModel):
    date: str
    message_count: int
    total_views: int
    total_forwards: int


class ChannelActivityResponse(BaseModel):
    channel_name: str
    total_posts: int
    avg_views: float
    daily_activity: List[DailyActivity]


class MessageSearchItem(BaseModel):
    message_id: str
    channel_name: str
    message_date: datetime
    message_text: Optional[str]
    views: int
    forwards: int


class MessageSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[MessageSearchItem]


class VisualContentChannelStat(BaseModel):
    channel_name: str
    total_messages: int
    messages_with_images: int
    image_percentage: float
    top_image_category: Optional[str] = None


class VisualContentResponse(BaseModel):
    total_channels: int
    channels: List[VisualContentChannelStat]
