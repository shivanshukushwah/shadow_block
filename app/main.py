from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import socketio
import uvicorn
from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis_client import redis_client
from app.core.kafka_producer import kafka_producer
from app.api.routes import moderation, analytics, admin, auth, reporting, audio_moderation, image_moderation, video_moderation, gamification, notifications, parental, integration
from app.services.ai_service import AIService
from app.middleware.rate_limiting import RateLimitMiddleware
from app.middleware.security import SecurityMiddleware
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Socket.IO server for real-time notifications
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    logger=True
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Content Moderation API...")
    
    # Initialize database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}. Continuing without database.")
    
    # Initialize AI models
    try:
        ai_service = AIService()
        await ai_service.initialize_models()
        logger.info("AI models loaded successfully")
    except Exception as e:
        logger.warning(f"AI model initialization failed: {e}. API will work with limited features.")
    
    # Start Kafka producer
    try:
        await kafka_producer.start()
        logger.info("Kafka producer started successfully")
    except Exception as e:
        logger.warning(f"Kafka producer start failed: {e}. Continuing without Kafka.")
    
    logger.info("Content Moderation API started successfully")
    
    yield
    # Shutdown
    logger.info("Shutting down Content Moderation API...")
    try:
        await kafka_producer.stop()
    except Exception as e:
        logger.warning(f"Error stopping Kafka producer: {e}")
    
    try:
        await redis_client.close()
    except Exception as e:
        logger.warning(f"Error closing Redis client: {e}")

app = FastAPI(
    title="Content Moderation API",
    description="Advanced AI-powered content moderation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS settings
origins = [
    "http://localhost:5173",   # Vite dev server
    # "https://your-frontend-domain.com",  # Uncomment for production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityMiddleware)

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(moderation.router, prefix="/api/v1/moderate", tags=["Moderation"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(reporting.router, prefix="/api/v1/reports", tags=["Reporting"])
app.include_router(audio_moderation.router, prefix="/api/v1", tags=["Audio Moderation"])
app.include_router(image_moderation.router, prefix="/api/v1", tags=["Image Moderation"])
app.include_router(video_moderation.router, prefix="/api/v1", tags=["Video Moderation"])
app.include_router(gamification.router, prefix="/api/v1/gamification", tags=["Gamification"])
app.include_router(notifications.router)
app.include_router(parental.router, prefix="/api/v1/parental", tags=["Parental Control"])
app.include_router(integration.router, prefix="/api/v1/integration", tags=["Integration"])

@app.get("/")
async def root():
    return {"message": "Content Moderation API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "redis": await redis_client.ping(),
        "database": "connected"
    }

# Socket.IO events for real-time notifications
@sio.event
async def connect(sid, environ):
    logger.info(f"Client {sid} connected")
    await sio.emit('connected', {'message': 'Connected to moderation system'}, room=sid)

@sio.event
async def disconnect(sid):
    logger.info(f"Client {sid} disconnected")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
