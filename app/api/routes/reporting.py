from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db, CrowdsourcedReport, User
from app.api.dependencies import get_current_user, require_moderator
from sqlalchemy import func
from app.api.routes.notifications import active_connections
from app.api.dependencies import require_admin

router = APIRouter()

REPORT_THRESHOLD = 3  # Number of unique reports to trigger auto-flag

@router.post("/report")
async def submit_report(
    content_id: str = Body(...),
    reason: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Prevent duplicate reports by same user
    existing = db.query(CrowdsourcedReport).filter_by(reporter_id=current_user.id, content_id=content_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already reported this content.")

    report = CrowdsourcedReport(
        reporter_id=current_user.id,
        content_id=content_id,
        reason=reason,
        status="pending",
        is_genuine=None
    )
    db.add(report)
    db.commit()

    # Automated cross-check: count unique reports for this content
    report_count = db.query(func.count(CrowdsourcedReport.id)).filter(
        CrowdsourcedReport.content_id == content_id
    ).scalar()

    if report_count >= REPORT_THRESHOLD:
        # Option 1: Auto-flag for moderator review (e.g., send notification)
        # Option 2: Auto-verify as genuine (if you trust the threshold)
        # Here, we just update status to "flagged"
        for r in db.query(CrowdsourcedReport).filter(CrowdsourcedReport.content_id == content_id, CrowdsourcedReport.status == "pending"):
            r.status = "flagged"
        db.commit()
        # Optionally, notify moderators here

    await send_alert(f"New report submitted for content {content_id}")

    return {"message": "Report submitted and pending review."}

@router.post("/review-report")
async def review_report(
    report_id: int = Body(...),
    status: str = Body(...),  # "resolved" or "rejected"
    db: Session = Depends(get_db),
    token_data: dict = Depends(require_moderator)
):
    report = db.query(CrowdsourcedReport).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = status
    db.commit()

    await send_alert(f"Report {report_id} status updated to {status}")

    return {"message": f"Report {status}."}

@router.post("/admin-action")
async def admin_action(
    # ...params...
    token_data: dict = Depends(require_admin)
):
    # Only admins can access
    ...

async def send_alert(message: str):
    for connection in active_connections:
        await connection.send_text(message)