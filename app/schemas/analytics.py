from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class CommunityHealthScore(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0, description="Overall health score")
    total_content: int = Field(..., description="Total content processed")
    blocked_percentage: float = Field(..., description="Percentage of blocked content")
    trend_direction: str = Field(..., description="improving, declining, or stable")
    risk_level: str = Field(..., description="low, medium, or high")
    top_issues: List[str] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=datetime.now)

class TrendAnalysis(BaseModel):
    period_days: int
    category: str
    trend_percentage: float = Field(..., description="Percentage change")
    daily_averages: List[float] = Field(default_factory=list)
    peak_hours: List[int] = Field(default_factory=list)
    seasonal_patterns: Dict[str, Any] = Field(default_factory=dict)

class HeatmapData(BaseModel):
    latitude: float
    longitude: float
    intensity: float = Field(..., ge=0.0, le=1.0)
    incident_count: int
    region: str

class ParentalReport(BaseModel):
    child_user_id: str
    report_period_days: int
    safety_score: float = Field(..., ge=0.0, le=100.0)
    total_interactions: int
    blocked_attempts: int
    concerning_patterns: List[str] = Field(default_factory=list)
    positive_behaviors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)

class AnalyticsResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
