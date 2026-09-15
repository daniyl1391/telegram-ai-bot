import logging
from bot.database import db

logger = logging.getLogger(__name__)

class PaymentManager:
    def create_payment(self, user_id, product_id, payment_method):
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            conn.close()
            return None
        
        try:
            cursor.execute("INSERT INTO payments (user_id, product_id, amount, payment_method) VALUES (?, ?, ?, ?)",
                         (user_id, product_id, product["price"], payment_method))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def confirm_payment(self, payment_id):
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        payment = cursor.fetchone()
        
        if not payment:
            conn.close()
            return False
        
        try:
            cursor.execute("UPDATE payments SET status = 'confirmed' WHERE id = ?", (payment_id,))
            
            cursor.execute("SELECT * FROM products WHERE id = ?", (payment["product_id"],))
            product = cursor.fetchone()
            
            db.create_subscription(payment["user_id"], "premium", product["messages_count"] or 1000, product["duration_days"])
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Payment error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

payment_manager = PaymentManager()
