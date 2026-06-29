import time
from core.db.manager import db
from modules.ai.schema import Model, ModelUsage, RateLimit
from sqlalchemy import select, func

class AIService:
    @staticmethod
    def get_or_create_model(provider: str, model_name: str) -> int:
        existing = db.get(Model, model_name=model_name)
        if existing:
            return existing["id"]
        return db.create(Model, provider=provider, model_name=model_name)

    @staticmethod
    def log_usage(model_id: int, prompt_tokens: int, completion_tokens: int, cost: float):
        db.create(ModelUsage, model_id=model_id, prompt_tokens=prompt_tokens, 
                  completion_tokens=completion_tokens, cost=cost, timestamp=time.time())

    @staticmethod
    def log_rate_limit(model_id: int, error_message: str):
        db.create(RateLimit, model_id=model_id, error_message=error_message, timestamp=time.time())

    @staticmethod
    def get_metrics_summary() -> dict:
        model_table = db.get_table(Model)
        usage_table = db.get_table(ModelUsage)
        rl_table = db.get_table(RateLimit)
        
        with next(db.get_session()) as session:
            usage_stmt = select(
                model_table.c.provider, model_table.c.model_name,
                func.sum(usage_table.c.prompt_tokens).label("total_prompt_tokens"),
                func.sum(usage_table.c.completion_tokens).label("total_completion_tokens"),
                func.sum(usage_table.c.cost).label("total_cost"),
                func.count(usage_table.c.id).label("total_requests")
            ).select_from(
                model_table.outerjoin(usage_table, model_table.c.id == usage_table.c.model_id)
            ).group_by(model_table.c.id)
            
            usage_data = [dict(r._mapping) for r in session.execute(usage_stmt).fetchall()]
            
            rl_stmt = select(
                model_table.c.model_name, rl_table.c.timestamp, rl_table.c.error_message
            ).select_from(
                rl_table.join(model_table, rl_table.c.model_id == model_table.c.id)
            ).order_by(rl_table.c.timestamp.desc()).limit(50)
            
            rate_limits = [dict(r._mapping) for r in session.execute(rl_stmt).fetchall()]
            
            return {"usage": usage_data, "rate_limits": rate_limits}

ai_service = AIService()
