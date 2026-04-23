import asyncio
import json
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database import Database
from handlers import router, setup_services
from redis_cache import ProfileCache
from mq import EventPublisher, EventConsumer
from ranking import recalculate_rating

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    config = load_config()

    if not config.bot_token:
        logger.error("BOT_TOKEN not set!")
        return

    db = Database(config.database_url)
    await db.create_tables()
    logger.info("Database tables created")

    try:
        profile_cache = ProfileCache(config.redis_url)
        await profile_cache.redis.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without cache.")
        profile_cache = None

    event_publisher = EventPublisher()
    event_consumer = EventConsumer()
    for attempt in range(5):
        try:
            await event_publisher.connect(config.rabbitmq_url)
            await event_consumer.connect(config.rabbitmq_url)
            logger.info("RabbitMQ connected successfully")
            break
        except Exception as e:
            if attempt < 4:
                logger.warning(f"RabbitMQ attempt {attempt + 1}/5 failed: {e}. Retrying in 3s...")
                await asyncio.sleep(3)
            else:
                logger.warning(f"RabbitMQ connection failed after 5 attempts. Running without MQ.")
                event_publisher = EventPublisher()
                event_consumer = EventConsumer()

    setup_services(profile_cache, event_publisher)

    async def on_mq_message(message):
        async with message.process():
            try:
                data = json.loads(message.body)
                async with db.session_factory() as session:
                    if "to_user_id" in data:
                        await recalculate_rating(session, data["to_user_id"])
                    if "from_user_id" in data:
                        await recalculate_rating(session, data["from_user_id"])
                    if "user_id" in data:
                        await recalculate_rating(session, data["user_id"])
            except Exception as e:
                logger.error(f"Error processing MQ message: {e}")

    if event_consumer.channel:
        await event_consumer.start_consuming(on_mq_message)

    bot = Bot(token=config.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(router)

    @dp.update.middleware()
    async def db_middleware(handler, event, data):
        async with db.session_factory() as session:
            data["session"] = session
            return await handler(event, data)

    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        if profile_cache:
            await profile_cache.close()
        await event_publisher.close()
        await event_consumer.close()


if __name__ == "__main__":
    asyncio.run(main())
