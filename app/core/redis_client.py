import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def get(self, key: str):
        """Get value from Redis"""
        if not self.redis:
            await self.connect()
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, ex: int = None):
        """Set value in Redis"""
        if not self.redis:
            await self.connect()
        return await self.redis.set(key, value, ex=ex)
    
    async def setex(self, key: str, time: int, value: str):
        """Set value with expiration"""
        if not self.redis:
            await self.connect()
        return await self.redis.setex(key, time, value)
    
    async def delete(self, key: str):
        """Delete key from Redis"""
        if not self.redis:
            await self.connect()
        return await self.redis.delete(key)
    
    async def ping(self):
        """Ping Redis"""
        if not self.redis:
            await self.connect()
        return await self.redis.ping()
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()

# Global instance
redis_client = RedisClient()
