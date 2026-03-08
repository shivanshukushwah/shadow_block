from sqlalchemy.orm import Session
from app.core.database import Content
from sqlalchemy import func

def count_total_contents(db: Session):
    return db.query(func.count(Content.id)).scalar()

def count_safe_contents(db: Session):
    return db.query(func.count(Content.id)).filter(Content.is_safe == True).scalar()

def count_abusive_contents(db: Session):
    return db.query(func.count(Content.id)).filter(Content.is_abusive == True).scalar()

def count_user_contents(db: Session, user_id: int, since=None):
    q = db.query(func.count(Content.id)).filter(Content.user_id == user_id)
    if since:
        q = q.filter(Content.created_at >= since)
    return q.scalar()

def count_user_safe_contents(db: Session, user_id: int, since=None):
    q = db.query(func.count(Content.id)).filter(Content.user_id == user_id, Content.is_safe == True)
    if since:
        q = q.filter(Content.created_at >= since)
    return q.scalar()

def count_user_abusive_contents(db: Session, user_id: int, since=None):
    q = db.query(func.count(Content.id)).filter(Content.user_id == user_id, Content.is_abusive == True)
    if since:
        q = q.filter(Content.created_at >= since)
    return q.scalar()

def get_abuse_counts_by_region(db: Session):
    return dict(
        db.query(Content.region, func.count(Content.id))
        .filter(Content.is_abusive == True)
        .group_by(Content.region)
        .all()
    )