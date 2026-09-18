from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Incident(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    severity: str
    service: str
    assigned_to: str
    created_at: str
    updated_at: str
    estimated_resolution: Optional[str] = None
    description: str
    impact: str
    workaround: Optional[str] = None
    tags: List[str] = []
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    category: str
    environment: str


class ServiceHealth(BaseModel):
    name: str
    display_name: str
    status: str  # healthy, degraded, down
    uptime_percent: float
    error_rate_percent: float
    p99_latency_ms: Optional[float] = None
    active_incidents: List[str] = []
    dependencies: List[str] = []
    team: str


class KnowledgeArticle(BaseModel):
    id: str
    title: str
    category: str
    tags: List[str] = []
    content: str
    steps: List[str] = []
    related_incidents: List[str] = []
    last_updated: str


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = []
    tools_used: List[str] = []
    conversation_id: str
