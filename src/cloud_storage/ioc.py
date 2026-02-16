from typing import AsyncIterable

import aioboto3
from aiobotocore.client import AioBaseClient
from dishka import AnyOf, Provider, Scope, from_context, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cloud_storage.application.interactors import CreateDirectoryInteractor, LoginUserInteractor, \
    RegisterUserInteractor, GetResourceInteractor, DeleteResourceInteractor, DownloadResourceInteractor, \
    MoveResourceInteractor, SearchResourceInteractor, UploadFileInteractor, ListDirectoryInteractor
from cloud_storage.application.interfaces import DBSession, FileStorageGateway, Hasher, SessionGateway, UserGateway, ArchiveGateway
from cloud_storage.config import Config
from cloud_storage.infrastructure.bcrypt_hasher import BcryptHasher
from cloud_storage.infrastructure.database.gateways import PgUserGateway
from cloud_storage.infrastructure.database.session import pg_session_maker
from cloud_storage.infrastructure.minio_gateway import MinioGateway
from cloud_storage.infrastructure.redis_gateway import RedisSessionGateway
from cloud_storage.infrastructure.zip_gateway import ZipGateway


class AppProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_hasher(self) -> Hasher:
        return BcryptHasher()


    @provide(scope=Scope.APP)
    async def get_redis_client(self, config: Config) -> AsyncIterable[Redis]:
        redis = Redis(host=config.redis.host, port=config.redis.port)
        try:
            yield redis
        finally:
            await redis.aclose()

    @provide(scope=Scope.REQUEST)
    def get_session_gateway(self, config: Config, redis_client: Redis) -> SessionGateway:
        return RedisSessionGateway(config=config.redis, redis_client=redis_client)

    @provide(scope=Scope.APP)
    def minio_session(self, config: Config) -> aioboto3.Session:
        return aioboto3.Session(
            aws_access_key_id=config.minio.access_key, aws_secret_access_key=config.minio.secret_key
        )

    @provide(scope=Scope.REQUEST)
    async def minio_client(self, minio_session: aioboto3.Session, config: Config) -> AsyncIterable[AioBaseClient]:
        async with minio_session.client(service_name="s3", endpoint_url=config.minio.endpoint) as s3:
            yield s3

    @provide(scope=Scope.REQUEST)
    def get_file_storage_gateway(self, config: Config, client: AioBaseClient) -> FileStorageGateway:
        return MinioGateway(client=client, config=config.minio)

    @provide(scope=Scope.REQUEST)
    def get_archive_gateway(self) -> ArchiveGateway:
        return ZipGateway()

    @provide(scope=Scope.APP)
    def get_session_maker(self, config: Config) -> async_sessionmaker[AsyncSession]:
        return pg_session_maker(pg_config=config.postgres)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AnyOf[AsyncSession, DBSession]]:
        async with session_maker() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def get_user_gateway(self, session: AsyncSession) -> UserGateway:
        return PgUserGateway(db_session=session)

    register_user = provide(RegisterUserInteractor, scope=Scope.REQUEST)
    login_user = provide(LoginUserInteractor, scope=Scope.REQUEST)
    create_directory = provide(CreateDirectoryInteractor, scope=Scope.REQUEST)
    get_resource = provide(GetResourceInteractor, scope=Scope.REQUEST)
    delete_resource = provide(DeleteResourceInteractor, scope=Scope.REQUEST)
    download_resource = provide(DownloadResourceInteractor, scope=Scope.REQUEST)
    move_resource = provide(MoveResourceInteractor, scope=Scope.REQUEST)
    upload_resource = provide(UploadFileInteractor, scope=Scope.REQUEST)
    search_resource = provide(SearchResourceInteractor, scope=Scope.REQUEST)
    list_directory = provide(ListDirectoryInteractor, scope=Scope.REQUEST)