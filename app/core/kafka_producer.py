import json
import asyncio
# from kafka import KafkaProducer
# from kafka.errors import KafkaError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AsyncKafkaProducer:
    def __init__(self):
        self.producer = None
        self.loop = None
    
    async def start(self):
        """Initialize Kafka producer"""
        try:
            self.loop = asyncio.get_event_loop()
            # self.producer = KafkaProducer(
            #     bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            #     value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            #     key_serializer=lambda k: k.encode('utf-8') if k else None,
            #     acks='all',
            #     retries=3,
            #     batch_size=16384,
            #     linger_ms=10,
            #     buffer_memory=33554432
            # )
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise
    
    async def send_message(self, topic: str, message: dict, key: str = None):
        """Send message to Kafka topic"""
        if not self.producer:
            logger.warning("Kafka producer not initialized")
            return
        
        try:
            future = self.producer.send(topic, value=message, key=key)
            # Run in executor to avoid blocking
            await self.loop.run_in_executor(None, future.get, 10)  # 10 second timeout
            logger.debug(f"Message sent to topic {topic}")
        except KafkaError as e:
            logger.error(f"Failed to send message to Kafka: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending to Kafka: {e}")
    
    async def stop(self):
        """Stop Kafka producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer stopped")

# Global instance
kafka_producer = AsyncKafkaProducer()
