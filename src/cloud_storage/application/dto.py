from dataclasses import dataclass


@dataclass(frozen=True)
class UserRegisterData:
    login: str
    password: str


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
