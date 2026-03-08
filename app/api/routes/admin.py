from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from uuid import uuid4
from app.core.database import get_db, Role, Permission, RolePermission, User
from app.api.dependencies import get_current_user, require_admin

router = APIRouter()

@router.post("/roles")
def create_role(
    name: str = Body(...),
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_admin)
):
    role = Role(name=name)
    db.add(role)
    db.commit()
    return {"message": f"Role '{name}' created."}

@router.post("/permissions")
def create_permission(
    name: str = Body(...),
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_admin)
):
    perm = Permission(name=name)
    db.add(perm)
    db.commit()
    return {"message": f"Permission '{name}' created."}

@router.post("/role-permission")
def assign_permission_to_role(
    role_id: int = Body(...),
    permission_id: int = Body(...),
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_admin)
):
    rp = RolePermission(role_id=role_id, permission_id=permission_id)
    db.add(rp)
    db.commit()
    return {"message": "Permission assigned to role."}

@router.post("/user-role")
def assign_role_to_user(
    user_id: int = Body(...),
    role_id: int = Body(...),
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_admin)
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role_id = role_id
    db.commit()
    return {"message": "Role assigned to user."}

@router.post("/rotate-api-key")
async def rotate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.api_key = str(uuid4())
    db.commit()
    return {"new_api_key": current_user.api_key}

@router.post("/admin/rotate-api-key")
async def admin_rotate_api_key(
    user_id: int,
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_admin)
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.api_key = str(uuid4())
    db.commit()
    return {"new_api_key": user.api_key}

@router.get("/admin/api-keys")
async def list_api_keys(
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_admin)
):
    users = db.query(User).all()
    return [{"user_id": u.id, "username": u.username, "api_key": u.api_key} for u in users]