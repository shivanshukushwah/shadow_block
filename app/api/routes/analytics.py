from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.core.database import get_db, ModerationLog, User, UserReport
from app.api.dependencies import get_current_user, require_moderator, get_current_user_token
from app.schemas.analytics import AnalyticsResponse, CommunityHealthScore
from app.services.analytics_service import AnalyticsService
from app.core.jwt_utils import verify_token

router = APIRouter()
security = HTTPBearer()

@router.get("/overview", response_model=AnalyticsResponse)
async def get_analytics_overview(
    days: int = Query(7, ge=1, le=365),
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
):
    """Get moderation analytics overview"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Basic statistics
    total_moderated = db.query(ModerationLog).filter(
        ModerationLog.created_at >= start_date
    ).count()
    
    blocked_content = db.query(ModerationLog).filter(
        and_(
            ModerationLog.created_at >= start_date,
            ModerationLog.action_taken == "block"
        )
    ).count()
    
    flagged_content = db.query(ModerationLog).filter(
        and_(
            ModerationLog.created_at >= start_date,
            ModerationLog.action_taken == "flag"
        )
    ).count()
    
    # Content type distribution
    content_type_stats = db.query(
        ModerationLog.content_type,
        func.count(ModerationLog.id).label('count')
    ).filter(
        ModerationLog.created_at >= start_date
    ).group_by(ModerationLog.content_type).all()
    
    # Violation type distribution
    violation_stats = {}
    logs_with_violations = db.query(ModerationLog).filter(
        and_(
            ModerationLog.created_at >= start_date,
            ModerationLog.violation_types.isnot(None)
        )
    ).all()
    
    for log in logs_with_violations:
        if log.violation_types:
            for violation in log.violation_types:
                violation_stats[violation] = violation_stats.get(violation, 0) + 1
    
    # Top offenders (users with most violations)
    top_offenders = db.query(
        ModerationLog.user_id,
        func.count(ModerationLog.id).label('violation_count')
    ).filter(
        and_(
            ModerationLog.created_at >= start_date,
            ModerationLog.action_taken.in_(["block", "flag"])
        )
    ).group_by(ModerationLog.user_id).order_by(
        func.count(ModerationLog.id).desc()
    ).limit(10).all()
    
    return AnalyticsResponse(
        total_content_moderated=total_moderated,
        blocked_content=blocked_content,
        flagged_content=flagged_content,
        approved_content=total_moderated - blocked_content - flagged_content,
        content_type_distribution=dict(content_type_stats),
        violation_type_distribution=violation_stats,
        top_offenders=[
            {"user_id": str(user_id), "violations": count} 
            for user_id, count in top_offenders
        ],
        period_days=days
    )

@router.get("/community-health", response_model=CommunityHealthScore)
async def get_community_health_score(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Calculate community health score"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total content in period
    total_content = db.query(ModerationLog).filter(
        ModerationLog.created_at >= start_date
    ).count()
    
    if total_content == 0:
        return CommunityHealthScore(
            health_score=100.0,
            toxicity_rate=0.0,
            improvement_trend=0.0,
            total_content=0,
            period_days=days
        )
    
    # Toxic content (blocked + flagged)
    toxic_content = db.query(ModerationLog).filter(
        and_(
            ModerationLog.created_at >= start_date,
            ModerationLog.action_taken.in_(["block", "flag"])
        )
    ).count()
    
    toxicity_rate = (toxic_content / total_content) * 100
    health_score = max(0, 100 - toxicity_rate)
    
    # Calculate trend (compare with previous period)
    previous_start = start_date - timedelta(days=days)
    previous_total = db.query(ModerationLog).filter(
        and_(
            ModerationLog.created_at >= previous_start,
            ModerationLog.created_at < start_date
        )
    ).count()
    
    previous_toxic = db.query(ModerationLog).filter(
        and_(
            ModerationLog.created_at >= previous_start,
            ModerationLog.created_at < start_date,
            ModerationLog.action_taken.in_(["block", "flag"])
        )
    ).count()
    
    improvement_trend = 0.0
    if previous_total > 0:
        previous_toxicity_rate = (previous_toxic / previous_total) * 100
        improvement_trend = previous_toxicity_rate - toxicity_rate
    
    return CommunityHealthScore(
        health_score=round(health_score, 2),
        toxicity_rate=round(toxicity_rate, 2),
        improvement_trend=round(improvement_trend, 2),
        total_content=total_content,
        period_days=days
    )

@router.get("/trends")
async def get_moderation_trends(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Get moderation trends over time"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily moderation counts
    daily_stats = db.query(
        func.date(ModerationLog.created_at).label('date'),
        func.count(ModerationLog.id).label('total'),
        func.sum(
            func.case(
                (ModerationLog.action_taken == 'block', 1),
                else_=0
            )
        ).label('blocked'),
        func.sum(
            func.case(
                (ModerationLog.action_taken == 'flag', 1),
                else_=0
            )
        ).label('flagged')
    ).filter(
        ModerationLog.created_at >= start_date
    ).group_by(
        func.date(ModerationLog.created_at)
    ).order_by(
        func.date(ModerationLog.created_at)
    ).all()
    
    trends = []
    for stat in daily_stats:
        trends.append({
            "date": stat.date.isoformat(),
            "total_content": stat.total,
            "blocked_content": stat.blocked or 0,
            "flagged_content": stat.flagged or 0,
            "toxicity_rate": round(((stat.blocked or 0) + (stat.flagged or 0)) / stat.total * 100, 2)
        })
    
    return {"trends": trends, "period_days": days}

@router.get("/user-reputation/{user_id}")
async def get_user_reputation(
    user_id: str,
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Get detailed user reputation and moderation history"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # User's moderation history
    moderation_history = db.query(ModerationLog).filter(
        ModerationLog.user_id == user_id
    ).order_by(ModerationLog.created_at.desc()).limit(50).all()
    
    # Violation counts
    violation_counts = {}
    for log in moderation_history:
        if log.violation_types:
            for violation in log.violation_types:
                violation_counts[violation] = violation_counts.get(violation, 0) + 1
    
    # Recent activity (last 30 days)
    recent_start = datetime.utcnow() - timedelta(days=30)
    recent_violations = db.query(ModerationLog).filter(
        and_(
            ModerationLog.user_id == user_id,
            ModerationLog.created_at >= recent_start,
            ModerationLog.action_taken.in_(["block", "flag"])
        )
    ).count()
    
    return {
        "user_id": user_id,
        "username": user.username,
        "reputation_score": user.reputation_score,
        "total_violations": len([log for log in moderation_history if log.action_taken in ["block", "flag"]]),
        "recent_violations": recent_violations,
        "violation_breakdown": violation_counts,
        "account_created": user.created_at.isoformat(),
        "is_active": user.is_active
    }

@router.get("/community-health-score")
def community_health_score(db=Depends(get_db)):
    analytics = AnalyticsService(db)
    score = analytics.calculate_community_health_score()
    return {"community_health_score": score}

@router.get("/abuse-heatmap")
def abuse_heatmap(db=Depends(get_db)):
    analytics = AnalyticsService(db)
    heatmap = analytics.get_abuse_heatmap()
    return heatmap

@router.get("/monthly-safe-behavior-report/{user_id}")
def monthly_safe_behavior_report(user_id: int, db=Depends(get_db)):
    analytics = AnalyticsService(db)
    report = analytics.get_monthly_safe_behavior_report(user_id)
    return report

@router.post("/review-report")
async def review_report(
    # ...params...
    token_data: dict = Depends(require_moderator)
):
    # Only moderators/admins can access
    ...
