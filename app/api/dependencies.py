from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.jwt_utils import verify_token
from sqlalchemy.orm import Session
from app.core.database import User, Permission, RolePermission, get_db
from datetime import datetime

security = HTTPBearer()

def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload

def require_moderator(token_data: dict = Depends(get_current_user_token)):
    if token_data.get("role") not in ["moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator or admin access required",
        )
    return token_data

def require_admin(token_data: dict = Depends(get_current_user_token)):
    if token_data.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return token_data

def require_permission(permission_name: str):
    def dependency(token_data: dict = Depends(get_current_user_token), db: Session = Depends(get_db)):
        user = db.query(User).filter_by(id=token_data["sub"]).first()
        role = user.role
        # Check if role has the required permission
        perm = db.query(Permission).filter_by(name=permission_name).first()
        has_perm = db.query(RolePermission).filter_by(role_id=role.id, permission_id=perm.id).first()
        if not has_perm:
            raise HTTPException(status_code=403, detail="Permission denied")
        return token_data
    return dependency

def require_api_key(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user or not user.api_key_active or user.api_key_expires_at < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Invalid, expired, or inactive API key")
    if user.api_key_usage_count >= user.api_key_usage_limit:
        raise HTTPException(status_code=429, detail="API key usage limit exceeded")
    user.api_key_usage_count += 1
    db.commit()
    if user.webhook_url:
        send_webhook_notification(user.webhook_url, "api_key_rotated", {"new_api_key": user.api_key})
    return user

def get_current_user(db: Session = Depends(get_db), token_data: dict = Depends(get_current_user_token)):
    user = db.query(User).filter_by(id=token_data["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user