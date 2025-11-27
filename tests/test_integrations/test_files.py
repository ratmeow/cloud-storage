import io
import uuid
import zipfile

import pytest
import pytest_asyncio
from aiobotocore.client import AioBaseClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cloud_storage.application.dto import MoveResourceDTO, UploadFileDTO, UserRegisterData
from cloud_storage.application.exceptions import (
    AlreadyExistsError,
    NotDirectoryError,
    NotFoundError,
    WrongPasswordError,
)
from cloud_storage.application.interactors import (
    CreateDirectoryInteractor,
    DeleteResourceInteractor,
    DownloadResourceInteractor,
    GetResourceInteractor,
    ListDirectoryInteractor,
    MoveResourceInteractor,
    SearchResourceInteractor,
    UploadFileInteractor,
)
from cloud_storage.config import Config
from cloud_storage.domain.models import ResourceType, User
from cloud_storage.domain.value_objects import Path
from cloud_storage.infrastructure.database.gateways import PgUserGateway
from cloud_storage.infrastructure.minio_gateway import MinioGateway
from cloud_storage.infrastructure.zip_gateway import ZipGateway


@pytest.fixture
def upload_file_interactor(pg_user_gateway: PgUserGateway, minio_gateway: MinioGateway) -> UploadFileInteractor:
    return UploadFileInteractor(user_gateway=pg_user_gateway, file_storage_gateway=minio_gateway)


@pytest.fixture
def create_directory_interactor(
    pg_user_gateway: PgUserGateway, minio_gateway: MinioGateway
) -> CreateDirectoryInteractor:
    return CreateDirectoryInteractor(user_gateway=pg_user_gateway, file_storage_gateway=minio_gateway)


@pytest.fixture
def get_resource_interactor(pg_user_gateway: PgUserGateway, minio_gateway: MinioGateway) -> GetResourceInteractor:
    return GetResourceInteractor(user_gateway=pg_user_gateway, file_storage_gateway=minio_gateway)


@pytest.fixture
def delete_resource_interactor(pg_user_gateway: PgUserGateway, minio_gateway: MinioGateway) -> DeleteResourceInteractor:
    return DeleteResourceInteractor(user_gateway=pg_user_gateway, file_storage_gateway=minio_gateway)


@pytest.fixture
def list_directory_interactor(pg_user_gateway: PgUserGateway, minio_gateway: MinioGateway) -> ListDirectoryInteractor:
    return ListDirectoryInteractor(user_gateway=pg_user_gateway, file_storage_gateway=minio_gateway)


@pytest.fixture
def download_resource_interactor(
    pg_user_gateway: PgUserGateway, minio_gateway: MinioGateway, zip_gateway: ZipGateway
) -> DownloadResourceInteractor:
    return DownloadResourceInteractor(
        user_gateway=pg_user_gateway, file_storage_gateway=minio_gateway, archive_gateway=zip_gateway
    )


@pytest.fixture
def search_resource_interactor(pg_user_gateway: PgUserGateway, minio_gateway: MinioGateway) -> SearchResourceInteractor:
    return SearchResourceInteractor(user_gateway=pg_user_gateway, file_storage_gateway=minio_gateway)


@pytest.fixture
def move_resource_interactor(pg_user_gateway: PgUserGateway, minio_gateway: MinioGateway) -> MoveResourceInteractor:
    return MoveResourceInteractor(user_gateway=pg_user_gateway, file_storage_gateway=minio_gateway)


@pytest_asyncio.fixture
async def exists_user(pg_session: AsyncSession) -> User:
    user_id = uuid.UUID(int=1)
    login = "test"
    hashed_password = "password_hashed"
    usr = User(login=login, hashed_password=hashed_password, id=user_id)
    pg_session.add(usr)
    await pg_session.commit()
    return usr


@pytest_asyncio.fixture
async def exists_file_system(exists_user: User, minio_client: AioBaseClient, config: Config):
    # folder1/
    # ├── test.txt
    # ├── test_upd.txt
    # ├── folder2/
    # │   └── test2.txt
    # └── folder3/
    #     └── test3.txt
    # └── folder4/

    bucket = config.minio.bucket
    directories = ["folder1/", "folder1/folder2/", "folder1/folder3/", "folder1/folder4/"]
    files_mapping: dict[str, bytes] = {
        "folder1/test.txt": b"Hello",
        "folder1/test_upd.txt": b"Hello World!",
        "folder1/folder2/test2.txt": b"Bob",
        "folder1/folder3/test3.txt": b"lala",
    }

    for directory in directories:
        await minio_client.put_object(Bucket=bucket, Key=str(exists_user.root_path.join(directory)), Body=b"")
    for file_name, file_content in files_mapping.items():
        await minio_client.put_object(Bucket=bucket, Key=str(exists_user.root_path.join(file_name)), Body=file_content)


class TestUploadFile:
    @pytest.mark.asyncio
    async def test_success(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        upload_file_interactor: UploadFileInteractor,
    ):
        interactor = upload_file_interactor
        file_name = "test.txt"
        file_content = b"Hello!"
        data = UploadFileDTO(user_id=str(exists_user.id), target_path=file_name, content=file_content)

        await interactor(data=data)

        storage_path = exists_user.root_path.join(file_name)
        result = await minio_client.get_object(Bucket=config.minio.bucket, Key=str(storage_path))
        assert result is not None
        result_data = await result["Body"].read()
        assert result_data == file_content

    @pytest.mark.asyncio
    async def test_not_exists_user(self, upload_file_interactor: UploadFileInteractor):
        interactor = upload_file_interactor
        file_name = "test.txt"
        file_content = b"Hello!"
        data = UploadFileDTO(user_id=str(uuid.UUID(int=1)), target_path=file_name, content=file_content)

        with pytest.raises(NotFoundError):
            await interactor(data=data)

    @pytest.mark.asyncio
    async def test_already_exists(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        upload_file_interactor: UploadFileInteractor,
        exists_file_system,
    ):
        interactor = upload_file_interactor
        file_name = "folder1/test.txt"
        file_content = b"Hello!"
        data = UploadFileDTO(user_id=str(exists_user.id), target_path=file_name, content=file_content)

        with pytest.raises(AlreadyExistsError):
            await interactor(data=data)

    @pytest.mark.asyncio
    async def test_with_directory(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        upload_file_interactor: UploadFileInteractor,
    ):
        interactor = upload_file_interactor
        file_path = "folder1/test.txt"
        directory_path = "folder1/"
        file_content = b"Hello!"
        data = UploadFileDTO(user_id=str(exists_user.id), target_path=file_path, content=file_content)

        await interactor(data=data)

        result = await minio_client.get_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(file_path))
        )
        assert result is not None
        result_data = await result["Body"].read()
        assert result_data == file_content
        directory = await minio_client.get_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(directory_path))
        )
        assert directory is not None


class TestCreateDirectory:
    @pytest.mark.asyncio
    async def test_success(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        create_directory_interactor: CreateDirectoryInteractor,
    ):
        interactor = create_directory_interactor
        directory_path = "folder1/folder2/"
        parent_directory_path = "folder1/"

        await interactor(path=directory_path, user_id=str(exists_user.id))

        result = await minio_client.get_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(directory_path))
        )
        assert result is not None
        parent_directory = await minio_client.get_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(parent_directory_path))
        )
        assert parent_directory is not None

    @pytest.mark.asyncio
    async def test_not_directory(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        create_directory_interactor: CreateDirectoryInteractor,
    ):
        interactor = create_directory_interactor
        directory_path = "folder1/folder2"

        with pytest.raises(NotDirectoryError):
            await interactor(path=directory_path, user_id=str(exists_user.id))

    @pytest.mark.asyncio
    async def test_already_exists(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        create_directory_interactor: CreateDirectoryInteractor,
        exists_file_system,
    ):
        interactor = create_directory_interactor
        directory_path = "folder1/folder2/"

        with pytest.raises(AlreadyExistsError):
            await interactor(path=directory_path, user_id=str(exists_user.id))


class TestGetResource:
    @pytest.mark.asyncio
    async def test_file(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        get_resource_interactor: GetResourceInteractor,
        exists_file_system,
    ):
        file_path = "folder1/test.txt"
        interactor = get_resource_interactor

        result = await interactor(path=file_path, user_id=str(exists_user.id))

        assert result is not None
        assert result.type == ResourceType.FILE
        assert result.size > 0

    @pytest.mark.asyncio
    async def test_directory(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        get_resource_interactor: GetResourceInteractor,
        exists_file_system,
    ):
        directory_path = "folder1/folder2/"
        interactor = get_resource_interactor

        result = await interactor(path=directory_path, user_id=str(exists_user.id))

        assert result is not None
        assert result.type == ResourceType.DIRECTORY


class TestDeleteResource:
    @pytest.mark.asyncio
    async def test_file(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        delete_resource_interactor: DeleteResourceInteractor,
        exists_file_system,
    ):
        file_path = "folder1/test.txt"
        interactor = delete_resource_interactor

        result = await interactor(path=file_path, user_id=str(exists_user.id))

        assert result is None
        with pytest.raises(Exception):
            await minio_client.head_object(Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(file_path)))

    @pytest.mark.asyncio
    async def test_directory(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        delete_resource_interactor: DeleteResourceInteractor,
        exists_file_system,
    ):
        directory_path = "folder1/folder2/"
        interactor = delete_resource_interactor

        result = await interactor(path=directory_path, user_id=str(exists_user.id))

        assert result is None
        with pytest.raises(Exception):
            await minio_client.head_object(
                Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(directory_path))
            )
        with pytest.raises(Exception):
            await minio_client.head_object(
                Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(directory_path + "test2.txt"))
            )


class TestListDirectory:
    @pytest.mark.asyncio
    async def test_success(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        list_directory_interactor: ListDirectoryInteractor,
        exists_file_system,
    ):
        dir_path = "folder1/"
        interactor = list_directory_interactor

        result = await interactor(path=dir_path, user_id=str(exists_user.id))

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_empty_directory(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        list_directory_interactor: ListDirectoryInteractor,
        exists_file_system,
    ):
        dir_path = "folder1/folder4/"
        interactor = list_directory_interactor

        result = await interactor(path=dir_path, user_id=str(exists_user.id))

        assert result is not None
        assert len(result) == 0


class TestDownloadResource:
    @pytest.mark.asyncio
    async def test_file(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        download_resource_interactor: DownloadResourceInteractor,
        exists_file_system,
    ):
        file_path = "folder1/test.txt"
        interactor = download_resource_interactor

        result = await interactor(path=file_path, user_id=str(exists_user.id))

        assert result is not None
        assert result == b"Hello"

    @pytest.mark.asyncio
    async def test_directory(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        download_resource_interactor: DownloadResourceInteractor,
        exists_file_system,
    ):
        dir_path = "folder1/"
        interactor = download_resource_interactor

        archive = await interactor(path=dir_path, user_id=str(exists_user.id))

        assert archive is not None
        archive_bytes = io.BytesIO(archive)
        with zipfile.ZipFile(archive_bytes, "r") as zipf:
            names = zipf.namelist()

            assert "test.txt" in names
            assert "folder2/" in names


class TestSearchResource:
    @pytest.mark.asyncio
    async def test_file(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        search_resource_interactor: SearchResourceInteractor,
        exists_file_system,
    ):
        file_search_name = "test2.txt"
        interactor = search_resource_interactor
        result = await interactor(resource_name=file_search_name, user_id=str(exists_user.id))

        assert result is not None
        assert len(result) == 1
        assert result[0].path.name == file_search_name

    @pytest.mark.asyncio
    async def test_directory(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        search_resource_interactor: SearchResourceInteractor,
        exists_file_system,
    ):
        dir_search_name = "folder1"
        interactor = search_resource_interactor
        result = await interactor(resource_name=dir_search_name, user_id=str(exists_user.id))

        assert result is not None
        assert len(result) == 1
        assert result[0].path.name == dir_search_name


class TestMoveResource:
    @pytest.mark.asyncio
    async def test_rename_file(
        self,
        config: Config,
        exists_user: User,
        exists_file_system,
        minio_client: AioBaseClient,
        move_resource_interactor: MoveResourceInteractor,
    ):
        current_file_path = "folder1/test.txt"
        new_file_path = "folder1/test_upd_yet.txt"
        interactor = move_resource_interactor
        data = MoveResourceDTO(user_id=str(exists_user.id), current_path=current_file_path, target_path=new_file_path)

        result = await interactor(data=data)

        assert result is not None
        with pytest.raises(Exception):
            await minio_client.head_object(
                Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(current_file_path))
            )
        renamed_file = await minio_client.head_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(new_file_path))
        )
        assert renamed_file is not None

    @pytest.mark.asyncio
    async def test_rename_directory(
        self,
        config: Config,
        exists_file_system,
        exists_user: User,
        minio_client: AioBaseClient,
        move_resource_interactor: MoveResourceInteractor,
    ):
        current_directory_path = "folder1/folder2/"
        new_directory_path = "folder1/folder2_1/"
        interactor = move_resource_interactor
        data = MoveResourceDTO(
            user_id=str(exists_user.id), current_path=current_directory_path, target_path=new_directory_path
        )

        result = await interactor(data=data)

        assert result is not None
        renamed_directory = await minio_client.head_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(new_directory_path))
        )
        assert renamed_directory is not None
        with pytest.raises(Exception):
            await minio_client.head_object(
                Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(current_directory_path))
            )
        with pytest.raises(Exception):
            await minio_client.head_object(
                Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(current_directory_path + "test2.txt"))
            )

    @pytest.mark.asyncio
    async def test_move_file(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        move_resource_interactor: MoveResourceInteractor,
        exists_file_system,
    ):
        current_file_path = "folder1/folder2/test2.txt"
        new_file_path = "folder1/folder3/test2.txt"
        interactor = move_resource_interactor
        data = MoveResourceDTO(user_id=str(exists_user.id), current_path=current_file_path, target_path=new_file_path)

        result = await interactor(data=data)

        assert result is not None
        moved_file = await minio_client.head_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(new_file_path))
        )
        assert moved_file is not None
        with pytest.raises(Exception):
            await minio_client.head_object(
                Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(current_file_path))
            )

    @pytest.mark.asyncio
    async def test_move_directory(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        move_resource_interactor: MoveResourceInteractor,
        exists_file_system,
    ):
        current_dir_path = "folder1/folder2/"
        new_dir_path = "folder1/folder3/folder2/"
        interactor = move_resource_interactor
        data = MoveResourceDTO(user_id=str(exists_user.id), current_path=current_dir_path, target_path=new_dir_path)

        result = await interactor(data=data)

        assert result is not None
        moved_dir = await minio_client.head_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(new_dir_path))
        )
        assert moved_dir is not None
        file_in_moved_dir = await minio_client.head_object(
            Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(new_dir_path + "test2.txt"))
        )
        assert file_in_moved_dir is not None
        with pytest.raises(Exception):
            await minio_client.head_object(
                Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(current_dir_path))
            )
        with pytest.raises(Exception):
            await minio_client.head_object(
                Bucket=config.minio.bucket, Key=str(exists_user.root_path.join(current_dir_path + "test2.txt"))
            )

    @pytest.mark.asyncio
    async def test_rename_file_already_exists(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        move_resource_interactor: MoveResourceInteractor,
        exists_file_system,
    ):
        current_file_path = "folder1/test.txt"
        new_file_path = "folder1/test_upd.txt"
        interactor = move_resource_interactor
        data = MoveResourceDTO(user_id=str(exists_user.id), current_path=current_file_path, target_path=new_file_path)

        with pytest.raises(AlreadyExistsError):
            await interactor(data=data)

    @pytest.mark.asyncio
    async def test_rename_directory_already_exists(
        self,
        config: Config,
        exists_user: User,
        minio_client: AioBaseClient,
        move_resource_interactor: MoveResourceInteractor,
        exists_file_system,
    ):
        current_dir_path = "folder1/folder2/"
        new_dir_path = "folder1/folder3/"
        interactor = move_resource_interactor
        data = MoveResourceDTO(user_id=str(exists_user.id), current_path=current_dir_path, target_path=new_dir_path)
        with pytest.raises(AlreadyExistsError):
            await interactor(data=data)
