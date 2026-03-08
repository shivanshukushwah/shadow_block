from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api.dependencies import require_api_key
from app.services.moderation_policy_service import ModerationPolicyService
from app.services.ai_service import AIService
from app.core.database import User

router = APIRouter()
ai_service = AIService()
policy_service = ModerationPolicyService()

@router.post("/external-integration")
async def external_integration(
    user: User = Depends(require_api_key),
    # ...other params...
):
    # Only accessible with a valid API key
    return {"message": "External integration successful"}

@router.post("/sdk/moderate-text")
async def sdk_moderate_text(
    text: str,
    mode: str = "medium",
    user: User = Depends(require_api_key)  # <-- Correct usage
):
    policy = policy_service.get_policy(mode)
    result = ai_service.predict_text(text)
    return {"result": result}

@router.post("/sdk/moderate-image")
async def sdk_moderate_image(
    file: UploadFile = File(...),
    mode: str = "medium",
    user = Depends(require_api_key)
):
    # ...image moderation logic...
    return {"result": "safe"}  # Example

