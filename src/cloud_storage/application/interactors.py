import uuid

from .interfaces import UserGateway, Hasher, DBSession, SessionGateway
from .dto import UserRegisterData, SessionDTO
from .exceptions import PasswordRequirementError, NotFoundError, WrongPasswordError, UserAlreadyExists
from cloud_storage.domain.models import User
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
            raise UserAlreadyExists()

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
    def __init__(self):
        pass

    async def __call__(self, path: str, user_id: str):
        pass