import uuid

import pytest
from redis.asyncio import Redis
import asyncio
from typing import Union, AsyncGenerator, AsyncIterable
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from cloud_storage.application.interactors import RegisterUserInteractor, LoginUserInteractor, LogoutUserInteractor
from cloud_storage.application.interfaces import DBSession
from cloud_storage.application.dto import UserRegisterData
from cloud_storage.infrastructure.bcrypt_hasher import BcryptHasher
from cloud_storage.infrastructure.database.gateways import PgUserGateway
from cloud_storage.infrastructure.redis_gateway import RedisSessionGateway
from cloud_storage.domain.models import User
from cloud_storage.config import Config
from cloud_storage.infrastructure.database.orm import mapper_registry
from cloud_storage.application.exceptions import PasswordRequirementError, UserAlreadyExists, NotFoundError, WrongPasswordError

@pytest.fixture(scope="session")
def config() -> Config:
    return Config.from_env("test.env")

@pytest.fixture(scope="session")
def hasher() -> BcryptHasher:
    return BcryptHasher()

@pytest_asyncio.fixture
async def session_maker_pg(config: Config) -> async_sessionmaker[AsyncSession | DBSession]:
    engine = create_async_engine(url=config.postgres.pg_async_url)
    async with engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.drop_all)
        await conn.run_sync(mapper_registry.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def pg_session(session_maker_pg) -> AsyncIterable[AsyncSession | DBSession]:
    async with session_maker_pg() as session:
        yield session

@pytest.fixture
def pg_user_gateway(pg_session) -> PgUserGateway:
    return PgUserGateway(db_session=pg_session)


@pytest.fixture
def register_user_interactor(hasher: BcryptHasher, pg_user_gateway: PgUserGateway, pg_session: DBSession) -> RegisterUserInteractor:
    return RegisterUserInteractor(user_gateway=pg_user_gateway,
                                  hasher=hasher,
                                  db_session=pg_session)

class TestRegisterUser:
    @pytest.mark.asyncio
    async def test_add_user(self, register_user_interactor: RegisterUserInteractor, pg_session: AsyncSession):
        login = "test"
        password = "password_1"
        interactor = register_user_interactor
        data = UserRegisterData(login=login, password=password)

        await interactor(register_data=data)

        result = await pg_session.execute(select(User).where(User.login == login))
        rows = result.fetchall()
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_not_strong_password(self, register_user_interactor: RegisterUserInteractor):
        login = "test"
        password = "test"
        interactor = register_user_interactor
        data = UserRegisterData(login=login, password=password)

        with pytest.raises(PasswordRequirementError):
            await interactor(register_data=data)

    @pytest.mark.asyncio
    async def test_user_already_exists(self, register_user_interactor: RegisterUserInteractor):
        login = "test"
        password = "password_1"
        interactor = register_user_interactor
        data = UserRegisterData(login=login, password=password)

        await interactor(register_data=data)

        with pytest.raises(UserAlreadyExists):
            await interactor(register_data=data)

@pytest_asyncio.fixture
async def redis_client(config: Config) -> AsyncIterable[Redis]:
    redis = Redis(host=config.redis.host, port=config.redis.port)
    await redis.flushdb()
    try:
        yield redis
    finally:
        await redis.aclose()

@pytest.fixture
def redis_session_gateway(redis_client: Redis, config: Config) -> RedisSessionGateway:
    return RedisSessionGateway(redis_client=redis_client, config=config.redis)


@pytest.fixture
def login_user_interactor(hasher: BcryptHasher, pg_user_gateway: PgUserGateway, redis_session_gateway: RedisSessionGateway) -> LoginUserInteractor:
    return LoginUserInteractor(user_gateway=pg_user_gateway,
                               hasher=hasher,
                               session_gateway=redis_session_gateway)


class TestLoginUser:
    @pytest.mark.asyncio
    async def test_success(self, login_user_interactor: LoginUserInteractor, pg_session: AsyncSession, hasher: BcryptHasher, redis_client: Redis):
        user_id = uuid.UUID(int=1)
        login = "test"
        password = "password_1"
        hashed_password = hasher.hash(password)
        pg_session.add(User(login=login, hashed_password=hashed_password, id=user_id))
        await pg_session.commit()
        interactor = login_user_interactor
        data = UserRegisterData(login=login, password=password)

        result = await interactor(login_data=data)

        assert result.user_id == user_id
        session = await redis_client.get(name=str(result.id))
        assert session is not None


    @pytest.mark.asyncio
    async def test_login_not_exists(self, login_user_interactor: LoginUserInteractor):
        login = "test"
        password = "password_1"
        interactor = login_user_interactor
        data = UserRegisterData(login=login, password=password)

        with pytest.raises(NotFoundError):
            await interactor(login_data=data)


    @pytest.mark.asyncio
    async def test_wrong_password(self, login_user_interactor: LoginUserInteractor, pg_session: AsyncSession, hasher: BcryptHasher):
        user_id = uuid.UUID(int=1)
        login = "test"
        password_true = "password_1"
        hashed_password = hasher.hash(password_true)
        pg_session.add(User(login=login, hashed_password=hashed_password, id=user_id))
        await pg_session.commit()
        interactor = login_user_interactor
        password_false = "password_2"
        data = UserRegisterData(login=login, password=password_false)

        with pytest.raises(WrongPasswordError):
            await interactor(login_data=data)

@pytest.fixture
def logout_user_interactor(redis_session_gateway: RedisSessionGateway) -> LogoutUserInteractor:
    return LogoutUserInteractor(session_gateway=redis_session_gateway)

class TestLogoutUser:
    @pytest.mark.asyncio
    async def test_success(self, logout_user_interactor: LogoutUserInteractor, redis_session_gateway: RedisSessionGateway, redis_client: Redis):

        user_id = uuid.UUID(int=1)
        session = await redis_session_gateway.create(user_id=user_id)
        interactor = logout_user_interactor

        await interactor(session_id=str(session.id))

        session = await redis_client.get(name=str(session.id))
        assert session is None