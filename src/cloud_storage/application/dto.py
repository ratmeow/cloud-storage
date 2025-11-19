import datetime
import uuid
from dataclasses import dataclass

@dataclass(frozen=True)
class UserRegisterData:
    login: str
    password: str


@dataclass
class SessionDTO:
    id: uuid.UUID
    user_id: uuid.UUID
    expired_ts: datetime.datetime