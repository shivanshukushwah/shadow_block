from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.video_moderation_service import VideoModerationService
import tempfile
from app.api.dependencies import get_current_user_token, get_db
from sqlalchemy.orm import Session

router = APIRouter()
# video_service = VideoModerationService()  # Lazy load

@router.post("/video/moderate")
async def moderate_video(file: UploadFile = File(...)):
    try:
        video_service = VideoModerationService()  # Instantiate here
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        result = video_service.moderate_video(tmp_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/some-user-feature")
async def some_user_feature(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
):
    # This endpoint is accessible to any authenticated user
    ...