import json
import logging
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

CACHE_PREFIX = "profiles"
CACHE_TTL = 300
BATCH_SIZE = 10


class ProfileCache:
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)

    async def close(self):
        await self.redis.aclose()

    def _key(self, user_id: int) -> str:
        return f"{CACHE_PREFIX}:{user_id}"

    async def get_next_profile(self, user_id: int) -> dict | None:
        key = self._key(user_id)
        data = await self.redis.lpop(key)
        if data:
            return json.loads(data)
        return None

    async def load_profiles(self, user_id: int, profiles: list[dict]):
        key = self._key(user_id)
        await self.redis.delete(key)

        if not profiles:
            return

        pipe = self.redis.pipeline()
        for p in profiles:
            pipe.rpush(key, json.dumps(p, ensure_ascii=False))
        pipe.expire(key, CACHE_TTL)
        await pipe.execute()

        logger.info(f"Cached {len(profiles)} profiles for user {user_id}")

    async def remaining(self, user_id: int) -> int:
        return await self.redis.llen(self._key(user_id))

    async def invalidate(self, user_id: int):
        await self.redis.delete(self._key(user_id))

    async def invalidate_all(self):
        keys = []
        async for key in self.redis.scan_iter(f"{CACHE_PREFIX}:*"):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cached profile lists")
