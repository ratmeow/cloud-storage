import uuid
from typing import Protocol
from cloud_storage.domain.models import User, Resource
from .dto import SessionDTO



class Hasher(Protocol):
    def hash(self, text: str) -> str:
        pass

    def verify_hash(self, original_text: str, hashed_text: str) -> bool:
        pass

class DBSession(Protocol):
    async def commit(self) -> None:
        pass


class UserGateway(Protocol):
    async def get_by_id(self, user_id: str) -> User | None:
        pass

    async def get_by_login(self, login: str) -> User | None:
        pass

    async def save(self, user: User) -> None:
        pass


class SessionGateway(Protocol):
    async def create(self, user_id: uuid.UUID) -> SessionDTO:
        pass

    async def delete(self, session_id: uuid.UUID) -> None:
        pass


class FileStorageGateway(Protocol):
    async def save_file(self, storage_path: str, content: bytes) -> None:
        pass

    async def get_file(self, storage_path: str) -> bytes:
        pass

    async def delete(self, storage_path: str) -> None:
        pass

    async def exists(self, storage_path: str) -> bool:
        pass

    async def move(self, from_path: str, to_path: str) -> None:
        pass

    async def list_directory(self, storage_path: str) -> list[str]:
        pass

    async def get_file_size(self, storage_path: str) -> int:
        pass

    async def create_directory(self, storage_path: str) -> None:
        pass

    async def list_directory_recursive(self, storage_path: str) -> list[str]:
        pass


class ArchiveGateway(Protocol):
    async def archive(self, folder: list) -> bytes:
        pass