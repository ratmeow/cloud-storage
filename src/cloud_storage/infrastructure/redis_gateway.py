import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from redis.asyncio import Redis

from cloud_storage.application.dto import SessionDTO
from cloud_storage.config import RedisConfig

logger = logging.getLogger(__name__)


class RedisInternalError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


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
        except Exception as e:
            logger.error(e)
            raise RedisInternalError

    async def get_user_id(self, session_id: str) -> str:
        try:
            session = await self.redis_client.get(session_id)
            return session.decode()
        except Exception as e:
            logger.error(e)
            raise RedisInternalError

    async def delete(self, session_id: str) -> None:
        try:
            await self.redis_client.delete(session_id)
        except Exception as e:
            logger.error(e)
            raise RedisInternalError
