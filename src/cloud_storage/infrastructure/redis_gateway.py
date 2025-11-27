import logging
import uuid
from datetime import UTC, datetime, timedelta

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

    async def create(self, user_id: uuid.UUID) -> SessionDTO:
        session_id = uuid.uuid4()
        try:
            await self.redis_client.setex(
                name=str(session_id), time=timedelta(seconds=self.lifetime), value=str(user_id)
            )
            return SessionDTO(
                id=session_id, user_id=user_id, expired_ts=datetime.now(UTC) + timedelta(seconds=self.lifetime)
            )
        except Exception as e:
            logger.error(e)
            raise RedisInternalError

    async def delete(self, session_id: uuid.UUID) -> None:
        try:
            await self.redis_client.delete(str(session_id))
        except Exception as e:
            logger.error(e)
            raise RedisInternalError
