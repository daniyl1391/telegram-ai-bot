from bot.config import ADMIN_USER_IDS
from bot.database import db

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS

async def add_ai_model(user_id: int, name: str, api_url: str, api_key: str, model_name: str):
    if not is_admin(user_id):
        return False
    db.add_ai_model(name, api_url, api_key, model_name)
    return True

async def add_product(user_id: int, name: str, description: str, price: int, 
                     duration_days: int, product_type: str, messages_count: int = 0):
    if not is_admin(user_id):
        return False
    return db.create_product(name, description, price, duration_days, product_type, messages_count)

async def set_default_ai_model(user_id: int, model_name: str):
    if not is_admin(user_id):
        return False
    db.set_setting("default_ai_model", model_name)
    return True
