import uuid
from typing import AsyncIterator, Protocol

from cloud_storage.domain.models import User
from cloud_storage.domain.value_objects import Path

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
    async def save_file(self, path: Path, content: bytes) -> None:
        pass

    async def get_file(self, path: Path) -> bytes:
        pass

    async def get_file_stream(self, path: Path) -> AsyncIterator[bytes]:
        pass

    async def delete(self, path: Path) -> None:
        pass

    async def exists(self, path: Path) -> bool:
        pass

    async def move(self, from_path: Path, to_path: Path) -> None:
        pass

    async def list_directory(self, path: Path) -> list[Path]:
        pass

    async def get_file_size(self, path: Path) -> int:
        pass

    async def create_directory(self, path: Path) -> None:
        pass

    async def list_directory_recursive(self, path: Path) -> list[Path]:
        pass


class ArchiveGateway(Protocol):
    async def archive(self, files: list[tuple[Path, bytes]]) -> bytes:
        pass

    def archive_stream(self, files: AsyncIterator[tuple[Path, AsyncIterator[bytes]]]) -> AsyncIterator[bytes]:
        pass
