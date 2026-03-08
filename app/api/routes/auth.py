from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from uuid import uuid4
from app.core.database import get_db, User
from app.api.dependencies import get_current_user, require_admin
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta = None):
    # data should include "role"
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/signup")
def signup(
    username: str = Body(...),
    email: str = Body(...),
    password: str = Body(...),
    consent_given: bool = Body(...),  # Must be True for GDPR
    date_of_birth: str = Body(...),   # Must be checked for COPPA
    db: Session = Depends(get_db)
):
    # GDPR: Require consent
    if not consent_given:
        raise HTTPException(status_code=400, detail="Consent required for signup (GDPR)")
    # COPPA: Age check (must be 13+)
    from datetime import datetime
    dob = datetime.strptime(date_of_birth, "%Y-%m-%d")
    age = (datetime.utcnow() - dob).days // 365
    if age < 13:
        raise HTTPException(status_code=400, detail="You must be at least 13 years old (COPPA)")
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    hashed_password = pwd_context.hash(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        consent_given=consent_given,        # <-- Save consent
        date_of_birth=dob                   # <-- Save DOB
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Signup successful", "user_id": str(user.id)}

@router.post("/login")
def login(
    username: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        # ...other claims...
    })
    return {"access_token": access_token, "token_type": "bearer"}

@router.delete("/delete-account")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.delete(current_user)
    db.commit()
    return {"message": "Account and personal data deleted (GDPR)"}

@router.get("/export-data")
def export_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Gather user data (profile, moderation logs, reports, etc.)
    user_data = {
        "profile": {
            "username": current_user.username,
            "email": current_user.email,
            "plan": current_user.plan,
            "date_of_birth": str(current_user.date_of_birth),
        },
        "moderation_logs": [
            {
                "content": log.content,
                "result": log.result,
                "timestamp": str(log.timestamp)
            }
            for log in db.query(ModerationLog).filter_by(user_id=current_user.id).all()
        ],
        "reports": [
            {
                "reason": report.reason,
                "status": report.status,
                "timestamp": str(report.created_at)
            }
            for report in db.query(UserReport).filter_by(reporter_id=current_user.id).all()
        ]
    }
    return user_data

@router.post("/parental-consent")
def parental_consent(
    child_id: str = Body(...),
    parent_email: str = Body(...),
    db: Session = Depends(get_db)
):
    # Store parental consent request, send email to parent, etc.
    # You can add a ParentalConsent model to track status
    return {"message": "Parental consent request submitted"}

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

@router.get("/api-key")
async def get_api_key(
    current_user: User = Depends(get_current_user)
):
    return {"api_key": current_user.api_key}

def log_audit_event(user_id, action, db):
    from app.core.database import AuditLog
    log = AuditLog(user_id=user_id, action=action, timestamp=datetime.utcnow())
    db.add(log)
    db.commit()