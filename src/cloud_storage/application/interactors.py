import uuid

from .interfaces import UserGateway, Hasher, DBSession, SessionGateway, FileStorageGateway, ArchiveGateway
from .dto import UserRegisterData, SessionDTO, UploadFileDTO, MoveResourceDTO
from .exceptions import PasswordRequirementError, NotFoundError, WrongPasswordError, AlreadyExistsError, NotDirectoryError
from cloud_storage.domain.models import User, Resource, ResourceType
from cloud_storage.domain.value_objects import Path
import re


class RegisterUserInteractor:
    def __init__(self, user_gateway: UserGateway, hasher: Hasher, db_session: DBSession):
        self.user_gateway = user_gateway
        self.hasher = hasher
        self.db_session = db_session

    async def __call__(self, register_data: UserRegisterData):
        if not self._is_strong_password(password=register_data.password):
            raise PasswordRequirementError()

        user = User(login=register_data.login,
                    hashed_password=self.hasher.hash(text=register_data.password))

        if await self.user_gateway.get_by_login(login=register_data.login) is not None:
            raise AlreadyExistsError()

        await self.user_gateway.save(user=user)
        await self.db_session.commit()

    @staticmethod
    def _is_strong_password(password: str) -> bool:
        pattern = r"^[A-Za-z\d!@#$%^&*_]{8,}$"
        has_required_char = bool(re.search(r"[\d!@#$%^&*_]", password))
        return bool(re.fullmatch(pattern, password)) and has_required_char

class LoginUserInteractor:
    def __init__(self, user_gateway: UserGateway, hasher: Hasher, session_gateway: SessionGateway):
        self.user_gateway = user_gateway
        self.hasher = hasher
        self.session_gateway = session_gateway


    async def __call__(self, login_data: UserRegisterData) -> SessionDTO:
        exist_user = await self.user_gateway.get_by_login(login=login_data.login)
        if not exist_user:
            raise NotFoundError(spec=f"User with login {login_data.login}")

        if not self.hasher.verify_hash(original_text=login_data.password, hashed_text=exist_user.hashed_password):
            raise WrongPasswordError()

        session = await self.session_gateway.create(user_id=exist_user.id)
        return session

class LogoutUserInteractor:
    def __init__(self, session_gateway: SessionGateway):
        self.session_gateway = session_gateway

    async def __call__(self, session_id: str) -> None:
        return await self.session_gateway.delete(session_id=uuid.UUID(session_id))

class GetResourceInteractor:
    def __init__(self, user_gateway: UserGateway, file_storage_gateway: FileStorageGateway):
        self.file_storage_gateway = file_storage_gateway
        self.user_gateway = user_gateway

    async def __call__(self, path: str, user_id: str) -> Resource:
        user = await self.user_gateway.get_by_id(user_id=user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id}")

        resource_path = Path(value=path)
        resource_full_path = user.root_path.join(resource_path)
        if not await self.file_storage_gateway.exists(storage_path=str(resource_full_path)):
            raise NotFoundError(f"Resource with path = {str(resource_path)}")

        resource = Resource(
            path=resource_path,
            type=ResourceType.DIRECTORY if resource_path.is_directory else ResourceType.FILE,
            size=None if resource_path.is_directory else await self.file_storage_gateway.get_file_size(str(resource_full_path))
        )

        return resource

class DeleteResourceInteractor:
    def __init__(self, user_gateway: UserGateway, file_storage_gateway: FileStorageGateway):
        self.file_storage_gateway = file_storage_gateway
        self.user_gateway = user_gateway

    async def __call__(self, path: str, user_id: str) -> None:
        user = await self.user_gateway.get_by_id(user_id=user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id}")

        resource_path = Path(value=path)
        resource_full_path = user.root_path.join(resource_path)
        if not await self.file_storage_gateway.exists(storage_path=str(resource_full_path)):
            raise NotFoundError(f"Resource with path = {str(resource_path)}")

        await self.file_storage_gateway.delete(str(resource_full_path))

class DownloadResourceInteractor:
    def __init__(self, user_gateway: UserGateway, file_storage_gateway: FileStorageGateway, archive_gateway: ArchiveGateway):
        self.file_storage_gateway = file_storage_gateway
        self.user_gateway = user_gateway
        self.archive_gateway = archive_gateway

    async def __call__(self, path: str, user_id: str) -> bytes:
        user = await self.user_gateway.get_by_id(user_id=user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id}")

        resource_path = Path(value=path)
        resource_full_path = user.root_path.join(resource_path)
        if not await self.file_storage_gateway.exists(storage_path=str(resource_full_path)):
            raise NotFoundError(f"Resource with path = {str(resource_path)}")

        if not resource_path.is_directory:
            return await self.file_storage_gateway.get_file(storage_path=str(resource_full_path))
        else:
            all_parts = await self.file_storage_gateway.list_directory_recursive(storage_path=str(resource_full_path))
            all_pairs = [(part, await self.file_storage_gateway.get_file(storage_path=str(resource_full_path.join(part)))) for part in all_parts]
            return await self.archive_gateway.archive(folder=all_pairs)

class UploadFileInteractor:
    def __init__(self, user_gateway: UserGateway, file_storage_gateway: FileStorageGateway):
        self.user_gateway = user_gateway
        self.file_storage_gateway = file_storage_gateway

    async def __call__(self, data: UploadFileDTO) -> Resource:
        user = await self.user_gateway.get_by_id(user_id=data.user_id)
        if not user:
            raise NotFoundError(f"User with id={data.user_id}")

        file_path = Path(value=data.target_path)
        file_path_full = user.root_path.join(file_path)
        if await self.file_storage_gateway.exists(storage_path=str(file_path_full)):
            raise AlreadyExistsError(spec=f"Resource {str(file_path)}")

        file_path_buf = file_path
        while not file_path_buf.is_root:
            parent = file_path_buf.parent
            parent_full_path = str(user.root_path.join(parent))
            if await self.file_storage_gateway.exists(storage_path=parent_full_path):
                break
            await self.file_storage_gateway.create_directory(storage_path=parent_full_path)
            file_path_buf = parent

        await self.file_storage_gateway.save_file(storage_path=str(file_path_full), content=data.content)
        resource = Resource(path=file_path, type=ResourceType.FILE, size=len(data.content))
        return resource

class CreateDirectoryInteractor:
    def __init__(self, user_gateway: UserGateway, file_storage_gateway: FileStorageGateway):
        self.file_storage_gateway = file_storage_gateway
        self.user_gateway = user_gateway

    async def __call__(self, path: str, user_id: str) -> Resource:
        user = await self.user_gateway.get_by_id(user_id=user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id}")

        directory_path = Path(value=path)
        if not directory_path.is_directory:
            raise NotDirectoryError()

        directory_full_path = user.root_path.join(directory_path)
        if await self.file_storage_gateway.exists(storage_path=str(directory_full_path)):
            raise AlreadyExistsError(spec=f"Directory {str(directory_path)}")

        directory_path_buf = directory_path
        while not directory_path_buf.is_root:
            parent = directory_path_buf.parent
            parent_full_path = str(user.root_path.join(parent))
            if await self.file_storage_gateway.exists(storage_path=parent_full_path):
                break
            await self.file_storage_gateway.create_directory(storage_path=parent_full_path)
            directory_path_buf = parent

        await self.file_storage_gateway.create_directory(storage_path=str(directory_full_path))
        return Resource(path=directory_path,
                        type=ResourceType.DIRECTORY,
                        size=None)

class ListDirectoryInteractor:
    def __init__(self, user_gateway: UserGateway, file_storage_gateway: FileStorageGateway):
        self.file_storage_gateway = file_storage_gateway
        self.user_gateway = user_gateway

    async def __call__(self, path: str, user_id: str) -> list[Resource]:
        user = await self.user_gateway.get_by_id(user_id=user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id}")

        directory_path = Path(value=path)
        if not directory_path.is_directory:
            raise NotDirectoryError()

        storage_path = user.root_path.join(directory_path)
        if not await self.file_storage_gateway.exists(storage_path=str(storage_path)):
            raise NotFoundError(f"Resource with path = {str(storage_path)}")

        child_paths = await self.file_storage_gateway.list_directory(storage_path=str(storage_path))
        resources = []
        for child_path in child_paths:
            user_path_value = child_path.replace(str(user.root_path), '', 1)
            user_path = Path(user_path_value)

            is_directory = child_path.endswith('/')

            resource = Resource(
                path=user_path,
                type=ResourceType.DIRECTORY if is_directory else ResourceType.FILE,
                size=None if is_directory else await self.file_storage_gateway.get_file_size(child_path)
            )
            resources.append(resource)

        return resources


class SearchResourceInteractor:
    def __init__(self, user_gateway: UserGateway, file_storage_gateway: FileStorageGateway):
        self.file_storage_gateway = file_storage_gateway
        self.user_gateway = user_gateway

    async def __call__(self, resource_name: str, user_id: str) -> list[Resource]:
        user = await self.user_gateway.get_by_id(user_id=user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id}")

        all_res = await self.file_storage_gateway.list_directory_recursive(storage_path=str(user.root_path))
        founded_res = [res for res in all_res if resource_name == Path(res).name]
        result = []
        for res in founded_res:
            path = Path(res)
            result.append(Resource(
                path=path,
                type=ResourceType.DIRECTORY if path.is_directory else ResourceType.FILE,
                size=None if path.is_directory else await self.file_storage_gateway.get_file_size(str(user.root_path.join(res)))
            ))

        return result


class MoveResourceInteractor:
    def __init__(self, user_gateway: UserGateway, file_storage_gateway: FileStorageGateway):
        self.file_storage_gateway = file_storage_gateway
        self.user_gateway = user_gateway

    async def __call__(self, data: MoveResourceDTO) -> Resource:
        user = await self.user_gateway.get_by_id(user_id=data.user_id)
        if not user:
            raise NotFoundError(f"User with id={data.user_id}")

        current_full_path = user.root_path.join(data.current_path)
        target_full_path = user.root_path.join(data.target_path)
        if not await self.file_storage_gateway.exists(storage_path=str(current_full_path)):
            raise NotFoundError(f"Resource with path = {str(data.current_path)}")

        if await self.file_storage_gateway.exists(storage_path=str(target_full_path)):
            raise AlreadyExistsError(spec=f"Directory {data.target_path}")

        await self.file_storage_gateway.move(from_path=str(current_full_path),
                                             to_path=str(target_full_path))

        target_path = Path(data.target_path)
        resource = Resource(
            path=target_path,
            type=ResourceType.DIRECTORY if target_path.is_directory else ResourceType.FILE,
            size=None if target_path.is_directory else await self.file_storage_gateway.get_file_size(str(target_full_path))
        )

        return resource