import logging
import aiohttp
from bot.database import db

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self):
        self.models = []
        self.load_models()
    
    def load_models(self):
        self.models = db.get_ai_models()
    
    async def chat(self, message, user_id, model_name=None):
        if not model_name:
            model_name = db.get_setting("default_ai_model") or "gpt"
        
        model = next((m for m in self.models if m["name"] == model_name), None)
        if not model:
            return "Error: Model not found"
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {model['api_key']}"}
                payload = {"message": message, "model": model["model_name"]}
                
                async with session.post(model["api_url"], json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "Error")
                    return "API Error"
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return "Service unavailable"

ai_manager = AIManager()
