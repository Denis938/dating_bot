import json
import logging
import aio_pika

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "dating_events"


class EventPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self, rabbitmq_url: str):
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        logger.info("Connected to RabbitMQ")

    async def close(self):
        if self.connection:
            await self.connection.close()

    async def publish(self, routing_key: str, data: dict):
        if not self.exchange:
            logger.warning("RabbitMQ not connected, skipping event")
            return

        message = aio_pika.Message(
            body=json.dumps(data, ensure_ascii=False).encode(),
            content_type="application/json",
        )
        await self.exchange.publish(message, routing_key=routing_key)
        logger.debug(f"Published event: {routing_key}")

    async def publish_profile_updated(self, user_id: int):
        await self.publish("profile.updated", {"user_id": user_id})

    async def publish_interaction(self, from_user_id: int, to_user_id: int, action: str):
        await self.publish(f"interaction.{action}", {
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "action": action,
        })

    async def publish_match_created(self, user1_id: int, user2_id: int):
        await self.publish("match.created", {
            "user1_id": user1_id,
            "user2_id": user2_id,
        })


class EventConsumer:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self, rabbitmq_url: str):
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        logger.info("EventConsumer connected to RabbitMQ")

    async def close(self):
        if self.connection:
            await self.connection.close()

    async def start_consuming(self, callback):
        exchange = await self.channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await self.channel.declare_queue("rating_updates", durable=True)

        await queue.bind(exchange, routing_key="interaction.*")
        await queue.bind(exchange, routing_key="profile.updated")
        await queue.bind(exchange, routing_key="match.created")

        await queue.consume(callback)
        logger.info("Started consuming rating update events")
