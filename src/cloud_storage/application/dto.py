import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class UserRegisterData:
    login: str
    password: str


@dataclass
class SessionDTO:
    id: str
    user_id: str
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
