import uuid
from abc import ABC, abstractmethod
from cloud_storage.domain.models import User
from .dto import SessionDTO


class Hasher(ABC):
    @abstractmethod
    def hash(self, text: str) -> str:
        pass

    @abstractmethod
    def verify_hash(self, original_text: str, hashed_text: str) -> bool:
        pass

class DBSession(ABC):
    @abstractmethod
    async def commit(self) -> None:
        pass


class UserGateway(ABC):
    @abstractmethod
    async def get_by_login(self, login: str) -> User | None:
        pass

    @abstractmethod
    async def save(self, user: User) -> None:
        pass


class SessionGateway(ABC):
    @abstractmethod
    async def create(self, user_id: uuid.UUID) -> SessionDTO:
        pass

    @abstractmethod
    async def delete(self, session_id: uuid.UUID) -> None:
        pass
