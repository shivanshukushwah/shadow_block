from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.image_moderation_service import ImageModerationService
import tempfile
from app.api.dependencies import get_current_user_token, get_db
from sqlalchemy.orm import Session

router = APIRouter()
# image_service = ImageModerationService()  # Lazy load

@router.post("/image/moderate")
async def moderate_image(file: UploadFile = File(...)):
    try:
        image_service = ImageModerationService()  # Instantiate here
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        ocr_text = image_service.extract_text(tmp_path)
        clip_classification = image_service.classify_image_clip(tmp_path)
        nsfw_classification = image_service.classify_image_nsfw(tmp_path)
        ocr_text_flagged = image_service.moderate_text(ocr_text) if ocr_text.strip() else False

        return {
            "ocr_text": ocr_text,
            "ocr_text_flagged": ocr_text_flagged,
            "clip_classification": clip_classification,
            "nsfw_classification": nsfw_classification
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/some-user-feature")
async def some_user_feature(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
):
    # This endpoint is accessible to any authenticated user
    ...