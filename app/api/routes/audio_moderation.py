from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.audio_moderation_service import AudioModerationService
import tempfile
import logging
# from app.dependencies import get_current_user_token, get_db
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_token, get_db

router = APIRouter()
_audio_service: AudioModerationService | None = None

def get_audio_service() -> AudioModerationService | None:
    global _audio_service
    if _audio_service is None:
        try:
            _audio_service = AudioModerationService()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"AudioModerationService init failed: {e}")
            _audio_service = None
    return _audio_service


@router.post("/audio/moderate")
async def moderate_audio(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        svc = get_audio_service()
        if svc is None:
            raise HTTPException(status_code=503, detail="Audio moderation unavailable")

        transcript = svc.transcribe(tmp_path)
        anger_score = svc.detect_anger(tmp_path)
        abusive_detected = svc.detect_abusive_content(transcript)

        return {
            "transcript": transcript,
            "anger_score": anger_score,
            "anger_detected": anger_score > 0.5,  # Adjust threshold as needed
            "abusive_detected": abusive_detected
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/some-user-feature")
async def some_user_feature(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
):
    # This endpoint is accessible to any authenticated user
    ...