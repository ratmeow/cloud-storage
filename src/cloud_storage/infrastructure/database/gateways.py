from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cloud_storage.domain.models import User


class PgUserGateway:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_by_login(self, login: str) -> User | None:
        query = select(User).filter_by(login=login)
        result = await self.db_session.execute(query)
        user = result.scalar_one_or_none()
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        user = await self.db_session.get(User, user_id)
        return user

    async def save(self, user: User) -> None:
        self.db_session.add(user)