import pytest
import asyncio
from typing import Union, AsyncGenerator, AsyncIterable
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from cloud_storage.application.interactors import RegisterUserInteractor
from cloud_storage.application.interfaces import DBSession
from cloud_storage.application.dto import UserRegisterData
from cloud_storage.infrastructure.bcrypt_hasher import BcryptHasher
from cloud_storage.infrastructure.database.gateways import PgUserGateway
from cloud_storage.domain.models import User
from cloud_storage.config import Config
from cloud_storage.infrastructure.database.orm import mapper_registry
from cloud_storage.application.exceptions import PasswordRequirementError, UserAlreadyExists

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
        await session.rollback()

@pytest.fixture
def pg_user_gateway(pg_session) -> PgUserGateway:
    return PgUserGateway(db_session=pg_session)


@pytest.fixture(scope="function")
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