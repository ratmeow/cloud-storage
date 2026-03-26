import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from cloud_storage.config import Config
from cloud_storage.domain.models import User
from cloud_storage.infrastructure.bcrypt_hasher import BcryptHasher


@pytest_asyncio.fixture(autouse=True)
async def clear_redis(redis_client: Redis) -> None:
    await redis_client.flushdb()


@pytest_asyncio.fixture
async def existing_user(pg_session: AsyncSession, hasher: BcryptHasher) -> User:
    user = User(login="test_user", hashed_password=hasher.hash("password_1"), id=uuid.UUID(int=1))
    pg_session.add(user)
    await pg_session.commit()
    return user


async def sign_in(http_client: AsyncClient, login: str, password: str):
    return await http_client.post("/api/sign-in", data={"login": login, "password": password})


class TestSession:
    @pytest.mark.asyncio
    async def test_create(
        self,
        http_client: AsyncClient,
        redis_client: Redis,
        config: Config,
        existing_user: User,
    ):
        response = await sign_in(http_client=http_client, login=existing_user.login, password="password_1")

        assert response.status_code == 200
        assert response.json() == {"username": existing_user.login}

        session_id = http_client.cookies.get("session_id")
        assert session_id is not None

        session_user_id = await redis_client.get(session_id)
        assert session_user_id == str(existing_user.id).encode()

        session_ttl = await redis_client.ttl(session_id)
        assert 0 < session_ttl <= config.redis.session_lifetime

    @pytest.mark.asyncio
    async def test_requires(self, http_client: AsyncClient):
        response = await http_client.get("/api/directory", params={"path": ""})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_use(self, http_client: AsyncClient, existing_user: User):
        sign_in_response = await sign_in(http_client=http_client, login=existing_user.login, password="password_1")
        protected_response = await http_client.post("/api/directory", params={"path": "folder1/"})

        assert sign_in_response.status_code == 200
        assert protected_response.status_code == 200
        assert protected_response.json() == {"path": "", "name": "folder1", "type": "directory", "size": None}

    @pytest.mark.asyncio
    async def test_delete(
        self,
        http_client: AsyncClient,
        redis_client: Redis,
        existing_user: User,
    ):
        sign_in_response = await sign_in(http_client=http_client, login=existing_user.login, password="password_1")
        session_id = http_client.cookies.get("session_id")

        assert sign_in_response.status_code == 200

        response = await http_client.post("/api/sign-out")

        assert response.status_code == 200
        assert await redis_client.get(session_id) is None
        assert http_client.cookies.get("session_id") is None
