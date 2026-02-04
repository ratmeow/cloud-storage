import re
import uuid
from dataclasses import dataclass, field
from enum import Enum

from .exceptions import DomainError
from .value_objects import Path


@dataclass
class User:
    login: str
    hashed_password: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self):
        self.validate()

    def validate(self):
        if not self._is_valid_login(self.login):
            raise DomainError(
                "Login must be at least 3 characters long, "
                "with only Latin letters, digits and special character(!@#$%^&*)."
            )

    @staticmethod
    def _is_valid_login(login: str) -> bool:
        pattern = r"^[A-Za-z\d!@#$%^&*]{3,}$"
        return bool(re.fullmatch(pattern, login))

    @property
    def root_path(self) -> Path:
        return Path(f"user-{str(self.id)}-files/")


class ResourceType(Enum):
    FILE = "file"
    DIRECTORY = "directory"


@dataclass
class Resource:
    path: Path
    type: ResourceType
    size: int | None = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        if self.type == ResourceType.FILE:
            if self.size is None:
                raise ValueError("File must have size")
            if self.path.is_directory:
                raise ValueError("File path cannot end with /")

        if self.type == ResourceType.DIRECTORY:
            if self.size is not None:
                raise ValueError("Directory cannot have size")
            if not self.path.is_directory:
                raise ValueError("Directory path must end with /")

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def parent_path(self) -> Path:
        return self.path.parent

    def to_dict(self) -> dict:
        result = {"path": str(self.parent_path), "name": self.name, "type": self.type.value}
        if self.size is not None:
            result["size"] = self.size
        return result
