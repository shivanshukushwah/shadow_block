#!/usr/bin/env python3
"""
Database initialization script
Creates all necessary tables and indexes for the moderation system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.database import Base, engine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_tables():
    """Create all database tables and indexes"""
    try:
        logger.info("Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create additional indexes for performance
        with engine.connect() as conn:
            # Index for moderation logs by user and date
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_moderation_logs_user_date 
                ON moderation_logs(user_id, created_at DESC);
            """))
            
            # Index for moderation logs by content type and action
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_moderation_logs_type_action 
                ON moderation_logs(content_type, action_taken);
            """))
            
            # Index for user reports by status
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_reports_status 
                ON user_reports(status, created_at DESC);
            """))
            
            # Index for user badges by user
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_badges_user 
                ON user_badges(user_id, badge_type);
            """))
            
            conn.commit()
        
        logger.info("Database tables and indexes created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def create_default_policies():
    """Create default moderation policies"""
    from sqlalchemy.orm import sessionmaker
    from app.core.database import ModerationPolicy
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if policies already exist
        existing_policies = session.query(ModerationPolicy).count()
        if existing_policies > 0:
            logger.info("Moderation policies already exist, skipping creation")
            return
        
        # Create default policies
        policies = [
            {
                "name": "strict",
                "description": "Strict moderation with low tolerance for violations",
                "rules": {
                    "toxicity_threshold": 0.3,
                    "auto_block": True,
                    "require_manual_review": False,
                    "allowed_violations": ["mild_profanity"]
                },
                "severity_level": "strict"
            },
            {
                "name": "medium",
                "description": "Balanced moderation for general communities",
                "rules": {
                    "toxicity_threshold": 0.5,
                    "auto_block": False,
                    "require_manual_review": True,
                    "allowed_violations": ["mild_profanity", "spam"]
                },
                "severity_level": "medium"
            },
            {
                "name": "lenient",
                "description": "Lenient moderation for mature communities",
                "rules": {
                    "toxicity_threshold": 0.7,
                    "auto_block": False,
                    "require_manual_review": True,
                    "allowed_violations": ["mild_profanity", "spam", "off_topic"]
                },
                "severity_level": "lenient"
            }
        ]
        
        for policy_data in policies:
            policy = ModerationPolicy(**policy_data)
            session.add(policy)
        
        session.commit()
        logger.info("Default moderation policies created successfully!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create default policies: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    create_database_tables()
    create_default_policies()
    print("Database initialization completed!")
