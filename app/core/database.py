from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
import uuid
from app.core.config import settings
from uuid import uuid4

# Detect database type
is_sqlite = "sqlite" in settings.DATABASE_URL

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if is_sqlite else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    # Use String(36) for UUIDs - works with both SQLite and PostgreSQL
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_moderator = Column(Boolean, default=False)
    reputation_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    points = Column(Integer, default=0)
    moderation_policy = Column(String, default="medium")  # "strict", "medium", or "lenient"
    plan = Column(String, default="free")  # "free" or "paid"
    role = Column(String, default="user")  # "user", "moderator", "admin"
    api_key = Column(String, unique=True, default=lambda: str(uuid4()))
    api_key_expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=90))
    api_key_active = Column(Boolean, default=True)
    consent_given = Column(Boolean, default=False)  # For GDPR consent
    date_of_birth = Column(DateTime, nullable=True) # For COPPA age check
    api_key_usage_count = Column(Integer, default=0)
    api_key_usage_limit = Column(Integer, default=10000)  # Example limit
    webhook_url = Column(String, nullable=True)

class ModerationLog(Base):
    __tablename__ = "moderation_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String, index=True)
    content_type = Column(String)  # text, image, video, audio
    original_content = Column(Text)
    user_id = Column(String(36), index=True)
    action_taken = Column(String)  # blocked, flagged, approved
    confidence_score = Column(Float)
    violation_types = Column(JSON)
    ai_explanation = Column(Text)
    moderator_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserReport(Base):
    __tablename__ = "user_reports"
    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(String(36), ForeignKey("users.id"))
    content_id = Column(String, index=True)
    reason = Column(String)
    status = Column(String, default="pending")  # pending, verified, rejected
    is_genuine = Column(Boolean, default=None)  # None until reviewed
    created_at = Column(DateTime, default=datetime.utcnow)

class ModerationPolicy(Base):
    __tablename__ = "moderation_policies"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True)
    description = Column(Text)
    rules = Column(JSON)
    severity_level = Column(String)  # strict, medium, lenient
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserBadge(Base):
    __tablename__ = "user_badges"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    badge_name = Column(String)
    awarded_at = Column(DateTime, default=datetime.utcnow)

class Content(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    region = Column(String, index=True)
    is_safe = Column(Boolean, default=True)
    is_abusive = Column(Boolean, default=False)
    created_at = Column(DateTime)
    user = relationship("User", back_populates="contents")

class RetrainingSample(Base):
    __tablename__ = "retraining_samples"
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(String, index=True)
    content_type = Column(String)  # "text", "image", etc.
    data = Column(Text)            # Raw text or path to file
    label = Column(String)         # e.g., "abusive", "hate"
    added_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    action = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)  # e.g., "user", "moderator", "admin"

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)  # e.g., "can_review_report", "can_delete_user"

class RolePermission(Base):
    __tablename__ = "role_permissions"
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    permission_id = Column(Integer, ForeignKey("permissions.id"))

class ParentalRelationship(Base):
    __tablename__ = "parental_relationships"
    id = Column(Integer, primary_key=True)
    parent_id = Column(String(36), ForeignKey("users.id"))
    child_id = Column(String(36), ForeignKey("users.id"))

class ChildControl(Base):
    __tablename__ = "child_controls"
    id = Column(Integer, primary_key=True)
    child_id = Column(String(36), ForeignKey("users.id"))
    feature = Column(String)
    blocked = Column(Boolean, default=False)

class CrowdsourcedReport(Base):
    __tablename__ = "crowdsourced_reports"
    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(String(36), ForeignKey("users.id"))
    content_id = Column(String)
    reason = Column(String)
    status = Column(String, default="pending")  # pending, verified, rejected
    created_at = Column(DateTime, default=datetime.utcnow)    

User.contents = relationship("Content", order_by=Content.id, back_populates="user")
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()









