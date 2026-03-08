from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
import os
import aiofiles
from datetime import datetime
import subprocess
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db, ModerationLog, User, UserBadge, RetrainingSample
from app.services.explainable_ai_service import ExplainableAIService
from app.services.moderation_policy_service import ModerationPolicyService
from app.services.ai_service import AIService
from app.core.kafka_producer import kafka_producer
from app.core.redis_client import redis_client
from app.api.dependencies import get_current_user, get_current_user_token, require_permission
from app.schemas.moderation import ModerationRequest, ModerationResponse
from app.core.config import settings
from app.services.audio_moderation_service import AudioModerationService

router = APIRouter()

# Initialize AI service lazily to avoid circular imports
_ai_service: AIService = None

def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        try:
            _ai_service = AIService()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize AIService: {e}")
            _ai_service = None
    return _ai_service

model = ...         # Load or import your ML model here
tokenizer = ...     # Load or import your tokenizer here
class_names = ...   # Define your class names here (e.g., ["toxic", "safe"])
explain_service = ExplainableAIService(model, tokenizer, class_names)
policy_service = ModerationPolicyService()

# instantiate audio service lazily to avoid heavy import-time work
_audio_service: AudioModerationService | None = None


def get_audio_service() -> AudioModerationService | None:
    global _audio_service
    if _audio_service is None:
        try:
            _audio_service = AudioModerationService()
        except Exception as e:
            # model load may fail due to MemoryError; log and continue without audio
            logger = logging.getLogger(__name__)
            logger.warning(f"Unable to initialize AudioModerationService: {e}")
            _audio_service = None
    return _audio_service

@router.post("/text", response_model=ModerationResponse)
async def moderate_text(
    request: ModerationRequest,
    background_tasks: BackgroundTasks = None,
    mode: str = None
):
    """Moderate text content"""
    try:
        content_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Get AI service lazily
        ai_service = get_ai_service()
        
        # Use AI service if available, otherwise fallback to testing response
        if ai_service:
            result = await ai_service.moderate_text(request.content)
        else:
            # Fallback for testing
            result = {
                "is_toxic": False,
                "action": "approve",
                "confidence": 0.95,
                "violations": [],
                "explanation": "AI service not available - using fallback"
            }
        
        is_flagged = result.get("is_toxic", False)
        
        if is_flagged:
            raise HTTPException(status_code=403, detail="Content flagged as toxic")
        
        return ModerationResponse(
            content_id=content_id,
            is_safe=not result.get("is_toxic", False),
            confidence=result.get("confidence", 0.9),
            violations=result.get("violations", []),
            action=result.get("action", "approve"),
            explanation=result.get("explanation", "Content moderated"),
            timestamp=timestamp
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 403) as-is
        raise
    except Exception as e:
        # Only catch unexpected errors and return 500
        raise HTTPException(status_code=500, detail=f"Moderation failed: {str(e)}")

@router.post("/upload", response_model=ModerationResponse)
async def moderate_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Moderate uploaded file (image, audio, video)"""
    try:
        # Validate file size
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1].lower()
        file_path = f"{settings.UPLOAD_DIR}/{file_id}.{file_extension}"
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Determine content type and moderate accordingly
        result = {}
        content_type = ""
        
        if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            content_type = "image"
            result = await ai_service.moderate_image(file_path)
        elif file_extension in ['mp3', 'wav', 'ogg', 'm4a']:
            content_type = "audio"
            result = await ai_service.moderate_audio(file_path)
        elif file_extension in ['mp4', 'avi', 'mov', 'wmv']:
            content_type = "video"
            result = await ai_service.moderate_video(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Create moderation log
        log_entry = ModerationLog(
            content_id=file_id,
            content_type=content_type,
            original_content=file.filename,
            user_id=current_user.id,
            action_taken=result["action"],
            confidence_score=result["confidence"],
            violation_types=result["violations"],
            ai_explanation=result.get("explanation", "File moderation completed")
        )
        
        db.add(log_entry)
        db.commit()
        
        # Clean up temporary file
        os.remove(file_path)
        
        return ModerationResponse(
            content_id=file_id,
            is_safe=not result.get("is_inappropriate", result.get("is_toxic", False)),
            confidence=result["confidence"],
            violations=result["violations"],
            action=result["action"],
            explanation=result.get("explanation", "File processed successfully")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File moderation failed: {str(e)}")

@router.get("/status/{content_id}")
async def get_moderation_status(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get moderation status for specific content"""
    
    # Check cache first
    cached_result = await redis_client.get(f"moderation:{content_id}")
    if cached_result:
        return {"status": "cached", "result": eval(cached_result)}
    
    # Check database
    log_entry = db.query(ModerationLog).filter(
        ModerationLog.content_id == content_id
    ).first()
    
    if not log_entry:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {
        "content_id": content_id,
        "action_taken": log_entry.action_taken,
        "confidence": log_entry.confidence_score,
        "violations": log_entry.violation_types,
        "created_at": log_entry.created_at
    }

@router.post("/batch")
async def moderate_batch(
    requests: List[ModerationRequest],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Moderate multiple text contents in batch"""
    results = []
    
    for request in requests:
        try:
            result = await ai_service.moderate_text(request.content)
            
            log_entry = ModerationLog(
                content_id=str(uuid.uuid4()),
                content_type="text",
                original_content=request.content,
                user_id=current_user.id,
                action_taken=result["action"],
                confidence_score=result["confidence"],
                violation_types=result["violations"],
                ai_explanation=result["explanation"]
            )
            
            db.add(log_entry)
            
            results.append(ModerationResponse(
                content_id=log_entry.content_id,
                is_safe=not result["is_toxic"],
                confidence=result["confidence"],
                violations=result["violations"],
                action=result["action"],
                explanation=result["explanation"]
            ))
            
        except Exception as e:
            results.append({
                "error": f"Failed to moderate content: {str(e)}",
                "content": request.content[:50] + "..."
            })
    
    db.commit()
    return {"results": results, "total": len(requests), "processed": len(results)}

@router.post("/explain")
def explain_message(
    text: str = Body(...), 
    method: str = Body("lime")
):
    if method == "shap":
        explanation = explain_service.explain_with_shap(text)
    else:
        explanation = explain_service.explain_with_lime(text)
    return {"explanation": explanation}

@router.post("/set-policy")
async def set_user_policy(
    policy: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if policy not in ["strict", "medium", "lenient"]:
        raise HTTPException(status_code=400, detail="Invalid policy")
    current_user.moderation_policy = policy
    db.commit()
    return {"message": f"Policy set to {policy}"}

@router.get("/some-user-feature")
async def some_user_feature(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
):
    # This endpoint is accessible to any authenticated user
    ...

@router.post("/review-report")
async def review_report(
    # ...params...
    token_data: dict = Depends(require_permission("can_review_report"))
):
    # Only users with "can_review_report" permission can access
    ...

@router.post("/moderate/audio")
async def moderate_audio(file: UploadFile = File(...)):
    # Save uploaded file temporarily
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())

    svc = get_audio_service()
    if svc is None:
        # model couldn't be loaded; return 503 so caller can retry later
        import os
        os.remove(file_location)
        raise HTTPException(status_code=503, detail="Audio moderation unavailable")

    try:
        transcript = svc.transcribe(file_location)
        anger_score = svc.detect_anger(file_location)
    finally:
        import os
        os.remove(file_location)

    return {
        "transcript": transcript,
        "anger_score": anger_score
    }
