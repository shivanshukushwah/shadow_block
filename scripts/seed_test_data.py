#!/usr/bin/env python3
"""
Seed test data for development and testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import sessionmaker
from app.core.database import engine, User, ModerationLog, UserReport, UserBadge
from passlib.context import CryptContext
import uuid
from datetime import datetime, timedelta
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_test_users():
    """Create test users"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if users already exist
        existing_users = session.query(User).count()
        if existing_users > 0:
            logger.info("Test users already exist, skipping creation")
            return
        
        users = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "hashed_password": pwd_context.hash("admin123"),
                "is_moderator": True,
                "reputation_score": 100.0
            },
            {
                "username": "moderator1",
                "email": "mod1@example.com",
                "hashed_password": pwd_context.hash("mod123"),
                "is_moderator": True,
                "reputation_score": 95.0
            },
            {
                "username": "user1",
                "email": "user1@example.com",
                "hashed_password": pwd_context.hash("user123"),
                "is_moderator": False,
                "reputation_score": 85.0
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "hashed_password": pwd_context.hash("user123"),
                "is_moderator": False,
                "reputation_score": 70.0
            },
            {
                "username": "problematic_user",
                "email": "problem@example.com",
                "hashed_password": pwd_context.hash("user123"),
                "is_moderator": False,
                "reputation_score": 30.0
            }
        ]
        
        created_users = []
        for user_data in users:
            user = User(**user_data)
            session.add(user)
            created_users.append(user)
        
        session.commit()
        logger.info(f"Created {len(created_users)} test users")
        return created_users
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create test users: {e}")
        raise
    finally:
        session.close()

def create_test_moderation_logs():
    """Create test moderation logs"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get users
        users = session.query(User).all()
        if not users:
            logger.error("No users found, create users first")
            return
        
        # Sample content and violations
        sample_content = [
            ("This is a great post!", "text", "approve", [], 0.1),
            ("I hate this stupid thing", "text", "flag", ["toxicity"], 0.6),
            ("You're an idiot and should die", "text", "block", ["toxicity", "threat"], 0.9),
            ("Check out this cool image", "image", "approve", [], 0.2),
            ("Inappropriate image content", "image", "block", ["nsfw"], 0.8),
            ("This video is awesome", "video", "approve", [], 0.1),
            ("Violent video content", "video", "block", ["violence"], 0.85),
            ("Nice audio clip", "audio", "approve", [], 0.15),
            ("Hate speech in audio", "audio", "block", ["hate_speech"], 0.9),
            ("Spam message buy now!", "text", "flag", ["spam"], 0.7)
        ]
        
        # Create logs for the past 30 days
        logs_created = 0
        for i in range(100):  # Create 100 test logs
            content, content_type, action, violations, confidence = random.choice(sample_content)
            user = random.choice(users)
            
            # Random date in the past 30 days
            days_ago = random.randint(0, 30)
            created_at = datetime.utcnow() - timedelta(days=days_ago)
            
            log = ModerationLog(
                content_id=str(uuid.uuid4()),
                content_type=content_type,
                original_content=content,
                user_id=user.id,
                action_taken=action,
                confidence_score=confidence,
                violation_types=violations,
                ai_explanation=f"Content {action}ed due to: {', '.join(violations) if violations else 'safe content'}",
                created_at=created_at
            )
            
            session.add(log)
            logs_created += 1
        
        session.commit()
        logger.info(f"Created {logs_created} test moderation logs")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create test moderation logs: {e}")
        raise
    finally:
        session.close()

def create_test_reports():
    """Create test user reports"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        users = session.query(User).all()
        if len(users) < 2:
            logger.error("Need at least 2 users to create reports")
            return
        
        reports_data = [
            {
                "reason": "harassment",
                "description": "User is sending threatening messages",
                "status": "pending"
            },
            {
                "reason": "spam",
                "description": "Posting promotional content repeatedly",
                "status": "reviewed"
            },
            {
                "reason": "hate_speech",
                "description": "Using discriminatory language",
                "status": "resolved"
            }
        ]
        
        reports_created = 0
        for report_data in reports_data:
            reporter = random.choice(users)
            reported_user = random.choice([u for u in users if u.id != reporter.id])
            
            report = UserReport(
                reporter_id=reporter.id,
                reported_content_id=str(uuid.uuid4()),
                reported_user_id=reported_user.id,
                reason=report_data["reason"],
                description=report_data["description"],
                status=report_data["status"]
            )
            
            session.add(report)
            reports_created += 1
        
        session.commit()
        logger.info(f"Created {reports_created} test reports")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create test reports: {e}")
        raise
    finally:
        session.close()

def create_test_badges():
    """Create test user badges"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        users = session.query(User).all()
        if not users:
            logger.error("No users found")
            return
        
        badge_types = [
            "safe_communicator",
            "helpful_reporter",
            "community_guardian",
            "positive_contributor"
        ]
        
        badges_created = 0
        for user in users[:3]:  # Give badges to first 3 users
            for badge_type in random.sample(badge_types, 2):  # 2 random badges per user
                badge = UserBadge(
                    user_id=user.id,
                    badge_type=badge_type,
                    points=random.randint(10, 100)
                )
                session.add(badge)
                badges_created += 1
        
        session.commit()
        logger.info(f"Created {badges_created} test badges")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create test badges: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Seeding test data...")
    create_test_users()
    create_test_moderation_logs()
    create_test_reports()
    create_test_badges()
    logger.info("Test data seeding completed!")
