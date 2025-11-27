from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cloud_storage.config import PostgresConfig


def pg_session_maker(pg_config: PostgresConfig) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(url=pg_config.pg_async_url)
    return async_sessionmaker(engine, expire_on_commit=False)
