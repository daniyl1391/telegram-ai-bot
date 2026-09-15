import logging
from datetime import datetime
from bot.database import db

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def check_messages_limit(self, user_id):
        sub = db.get_subscription(user_id)
        if not sub:
            return False
        
        if sub["expire_date"]:
            expire = datetime.fromisoformat(sub["expire_date"])
            if expire < datetime.now():
                return False
        
        return sub["message_used"] < sub["message_limit"]
    
    def increment_message(self, user_id):
        sub = db.get_subscription(user_id)
        if sub:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE subscriptions SET message_used = message_used + 1 WHERE id = ?", (sub["id"],))
            conn.commit()
            conn.close()
    
    def create_free(self, user_id):
        db.create_subscription(user_id, "free", 10, duration_days=30)

subscription_manager = SubscriptionManager()
