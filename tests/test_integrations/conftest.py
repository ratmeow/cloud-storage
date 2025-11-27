from typing import AsyncGenerator, AsyncIterable, Union

import aioboto3
import pytest
import pytest_asyncio
from aiobotocore.client import AioBaseClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cloud_storage.application.interfaces import DBSession
from cloud_storage.config import Config
from cloud_storage.infrastructure.bcrypt_hasher import BcryptHasher
from cloud_storage.infrastructure.database.gateways import PgUserGateway
from cloud_storage.infrastructure.database.orm import mapper_registry
from cloud_storage.infrastructure.minio_gateway import MinioGateway
from cloud_storage.infrastructure.redis_gateway import RedisSessionGateway
from cloud_storage.infrastructure.zip_gateway import ZipGateway


@pytest.fixture(scope="session")
def config() -> Config:
    return Config.from_env("test.env")


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


@pytest.fixture(scope="session")
def hasher() -> BcryptHasher:
    return BcryptHasher()


@pytest.fixture(scope="session")
def minio_session(config: Config) -> aioboto3.Session:
    return aioboto3.Session(aws_access_key_id=config.minio.access_key, aws_secret_access_key=config.minio.secret_key)


@pytest_asyncio.fixture
async def minio_client(minio_session: aioboto3.Session, config: Config) -> AsyncIterable[AioBaseClient]:
    async with minio_session.client(service_name="s3", endpoint_url=config.minio.endpoint) as s3:
        resp = await s3.list_objects_v2(Bucket=config.minio.bucket)
        if "Contents" in resp:
            await s3.delete_objects(
                Bucket=config.minio.bucket, Delete={"Objects": [{"Key": o["Key"]} for o in resp["Contents"]]}
            )
        yield s3


@pytest.fixture
def minio_gateway(minio_client: AioBaseClient, config: Config) -> MinioGateway:
    return MinioGateway(client=minio_client, config=config.minio)


@pytest.fixture
def zip_gateway() -> ZipGateway:
    return ZipGateway()


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
