import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from redis.asyncio import Redis, RedisError

from cloud_storage.application.exceptions import ApplicationError
from cloud_storage.config import RedisConfig

from .dto import SessionDTO

logger = logging.getLogger(__name__)


class RedisSessionGateway:
    def __init__(self, redis_client: Redis, config: RedisConfig):
        self.redis_client = redis_client
        self.lifetime = config.session_lifetime

    async def create(self, user_id: str) -> SessionDTO:
        session_id = str(uuid4())
        try:
            await self.redis_client.setex(name=session_id, time=timedelta(seconds=self.lifetime), value=user_id)
            return SessionDTO(
                id=session_id, user_id=user_id, expired_ts=datetime.now(UTC) + timedelta(seconds=self.lifetime)
            )
        except RedisError as e:
            logger.error("Redis Internal Error:", e)
            raise ApplicationError()

    async def get_user_id(self, session_id: str) -> str:
        try:
            session = await self.redis_client.get(session_id)
            if session is None:
                logger.error("Not found session:", session_id)
                raise ApplicationError()
            return session.decode()
        except RedisError as e:
            logger.error("Redis Internal Error:", e)
            raise ApplicationError()

    async def delete(self, session_id: str) -> None:
        try:
            await self.redis_client.delete(session_id)
        except RedisError as e:
            logger.error("Redis Internal Error:", e)
            raise ApplicationError()
