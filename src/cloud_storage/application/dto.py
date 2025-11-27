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

@dataclass
class UploadFileDTO:
    user_id: str
    target_path: str
    content: bytes

@dataclass
class MoveResourceDTO:
    user_id: str
    current_path: str
    target_path: str