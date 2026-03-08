from datetime import datetime, timedelta
from app.core.db_queries import (
    count_total_contents, count_safe_contents, count_abusive_contents,
    count_user_contents, count_user_safe_contents, count_user_abusive_contents,
    get_abuse_counts_by_region
)

class AnalyticsService:
    def __init__(self, db_session):
        self.db = db_session

    def calculate_community_health_score(self):
        total = count_total_contents(self.db)
        safe = count_safe_contents(self.db)
        abusive = count_abusive_contents(self.db)
        if total == 0:
            return 100
        score = (safe / total) * 100 - (abusive / total) * 50
        return max(0, min(100, score))

    def get_monthly_safe_behavior_report(self, user_id):
        now = datetime.utcnow()
        last_month = now - timedelta(days=30)
        total = count_user_contents(self.db, user_id, since=last_month)
        safe = count_user_safe_contents(self.db, user_id, since=last_month)
        abusive = count_user_abusive_contents(self.db, user_id, since=last_month)
        return {
            "user_id": user_id,
            "month": now.strftime("%B %Y"),
            "total_contents": total,
            "safe_contents": safe,
            "abusive_contents": abusive,
            "safe_percentage": (safe / total * 100) if total else 100
        }

    def get_abuse_heatmap(self):
        return get_abuse_counts_by_region(self.db)