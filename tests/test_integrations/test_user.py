import uuid

import pytest
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cloud_storage.application.dto import UploadFileDTO, UserRegisterData
from cloud_storage.application.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    PasswordRequirementError,
    WrongPasswordError,
)
from cloud_storage.application.interactors import LoginUserInteractor, LogoutUserInteractor, RegisterUserInteractor
from cloud_storage.application.interfaces import DBSession
from cloud_storage.domain.models import User
from cloud_storage.infrastructure.bcrypt_hasher import BcryptHasher
from cloud_storage.infrastructure.database.gateways import PgUserGateway
from cloud_storage.infrastructure.redis_gateway import RedisSessionGateway


@pytest.fixture
def register_user_interactor(
    hasher: BcryptHasher, pg_user_gateway: PgUserGateway, pg_session: DBSession
) -> RegisterUserInteractor:
    return RegisterUserInteractor(user_gateway=pg_user_gateway, hasher=hasher, db_session=pg_session)


@pytest.fixture
def login_user_interactor(
    hasher: BcryptHasher, pg_user_gateway: PgUserGateway, redis_session_gateway: RedisSessionGateway
) -> LoginUserInteractor:
    return LoginUserInteractor(user_gateway=pg_user_gateway, hasher=hasher, session_gateway=redis_session_gateway)


@pytest.fixture
def logout_user_interactor(redis_session_gateway: RedisSessionGateway) -> LogoutUserInteractor:
    return LogoutUserInteractor(session_gateway=redis_session_gateway)


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

        with pytest.raises(AlreadyExistsError):
            await interactor(register_data=data)


class TestLoginUser:
    @pytest.mark.asyncio
    async def test_success(
        self,
        login_user_interactor: LoginUserInteractor,
        pg_session: AsyncSession,
        hasher: BcryptHasher,
        redis_client: Redis,
    ):
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
    async def test_wrong_password(
        self, login_user_interactor: LoginUserInteractor, pg_session: AsyncSession, hasher: BcryptHasher
    ):
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


class TestLogoutUser:
    @pytest.mark.asyncio
    async def test_success(
        self,
        logout_user_interactor: LogoutUserInteractor,
        redis_session_gateway: RedisSessionGateway,
        redis_client: Redis,
    ):
        user_id = uuid.UUID(int=1)
        session = await redis_session_gateway.create(user_id=user_id)
        interactor = logout_user_interactor

        await interactor(session_id=str(session.id))

        session = await redis_client.get(name=str(session.id))
        assert session is None
