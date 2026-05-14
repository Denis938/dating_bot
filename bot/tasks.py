import asyncio
import logging
from celery import Celery
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from config import load_config
from database import User, Database
from ranking import recalculate_rating

logger = logging.getLogger(__name__)
config = load_config()

app = Celery("dating_tasks", broker=config.rabbitmq_url, backend=config.redis_url)

app.conf.beat_schedule = {
    "recalculate-ratings-every-30-mins": {
        "task": "tasks.recalculate_all_ratings_task",
        "schedule": 1800.0,  # 30 minutes
    },
}
app.conf.timezone = "UTC"

# Sync engine for Celery (worker threads)
engine = create_engine(config.sync_database_url)
SessionLocal = sessionmaker(bind=engine)


@app.task
def recalculate_all_ratings_task():
    """Background task to recalculate all user ratings."""
    with SessionLocal() as session:
        result = session.execute(select(User.id))
        user_ids = [row[0] for row in result.fetchall()]

    async def run_updates():
        async_db = Database(config.database_url)
        try:
            async with async_db.session_factory() as async_session:
                for user_id in user_ids:
                    try:
                        await recalculate_rating(async_session, user_id)
                    except Exception as e:
                        logger.exception("Error updating rating for user %s: %s", user_id, e)
        finally:
            await async_db.engine.dispose()

    asyncio.run(run_updates())
    return f"Updated {len(user_ids)} ratings"
