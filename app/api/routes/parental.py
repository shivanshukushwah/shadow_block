from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db, ParentalRelationship, ChildControl, ModerationLog, User
from app.api.dependencies import get_current_user


router = APIRouter()


@router.get("/parental/report/{child_id}")
async def get_child_report(
    child_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if current_user is parent of child_id (implement relationship logic)
    # Example: if not current_user.is_parent_of(child_id): raise HTTPException(...)
    logs = db.query(ModerationLog).filter(ModerationLog.user_id == child_id).all()
    safe_count = sum(1 for log in logs if log.is_safe)
    abusive_count = sum(1 for log in logs if log.is_abusive)
    return {
        "child_id": child_id,
        "safe_contents": safe_count,
        "abusive_contents": abusive_count,
        "total_contents": len(logs),
        "safe_percentage": (safe_count / len(logs) * 100) if logs else 100
    }


@router.post("/parental/block/{child_id}")
async def block_child_feature(
    child_id: str,
    feature: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Implement logic to block a feature for the child
    # Example: update child settings in DB
    return {"message": f"Feature '{feature}' blocked for child {child_id}"}


@router.get("/dashboard/{child_id}")
async def parental_dashboard(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check parental relationship
    rel = db.query(ParentalRelationship).filter_by(parent_id=current_user.id, child_id=child_id).first()
    if not rel:
        raise HTTPException(status_code=403, detail="Not authorized for this child")
    logs = db.query(ModerationLog).filter_by(user_id=child_id).all()
    safe_count = sum(1 for log in logs if log.is_safe)
    abusive_count = sum(1 for log in logs if log.is_abusive)
    controls = db.query(ChildControl).filter_by(child_id=child_id).all()
    blocked_features = [c.feature for c in controls if c.blocked]
    return {
        "child_id": child_id,
        "safe_contents": safe_count,
        "abusive_contents": abusive_count,
        "total_contents": len(logs),
        "blocked_features": blocked_features
    }


@router.post("/block-feature")
async def block_child_feature(
    child_id: int = Body(...),
    feature: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rel = db.query(ParentalRelationship).filter_by(parent_id=current_user.id, child_id=child_id).first()
    if not rel:
        raise HTTPException(status_code=403, detail="Not authorized for this child")
    control = db.query(ChildControl).filter_by(child_id=child_id, feature=feature).first()
    if not control:
        control = ChildControl(child_id=child_id, feature=feature, blocked=True)
        db.add(control)
    else:
        control.blocked = True
    db.commit()
    return {"message": f"Feature '{feature}' blocked for child {child_id}"}