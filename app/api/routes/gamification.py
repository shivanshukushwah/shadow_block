from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, User
from app.api.dependencies import get_current_user_token

router = APIRouter()

@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.points.desc()).limit(10).all()
    return [
        {
            "username": u.username,
            "points": u.points
        }
        for u in users
    ]

@router.get("/some-user-feature")
async def some_user_feature(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
):
    # This endpoint is accessible to any authenticated user
    ...