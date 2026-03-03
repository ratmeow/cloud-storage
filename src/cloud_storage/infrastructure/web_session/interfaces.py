from typing import Protocol

from .dto import SessionDTO


class SessionGateway(Protocol):
    async def create(self, user_id: str) -> SessionDTO:
        pass

    async def get_user_id(self, session_id: str) -> str:
        pass

    async def delete(self, session_id: str) -> None:
        pass
