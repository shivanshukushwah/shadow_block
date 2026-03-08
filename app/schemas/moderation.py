from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class ModerationRequest(BaseModel):
    content: str
    content_type: Optional[str] = "text"
    metadata: Optional[Dict[str, Any]] = {}

class ModerationResponse(BaseModel):
    content_id: str
    is_safe: bool
    confidence: float
    violations: List[str]
    action: str  # approve, flag, block
    explanation: str
    timestamp: Optional[datetime] = None

class AnalyticsResponse(BaseModel):
    total_content_moderated: int
    blocked_content: int
    flagged_content: int
    approved_content: int
    content_type_distribution: Dict[str, int]
    violation_type_distribution: Dict[str, int]
    top_offenders: List[Dict[str, Any]]
    period_days: int

class CommunityHealthScore(BaseModel):
    health_score: float  # 0-100
    toxicity_rate: float  # percentage
    improvement_trend: float  # positive = improving
    total_content: int
    period_days: int

class UserReportRequest(BaseModel):
    reported_content_id: str
    reported_user_id: Optional[str] = None
    reason: str
    description: Optional[str] = None

class UserReportResponse(BaseModel):
    report_id: str
    status: str
    created_at: datetime
    message: str
