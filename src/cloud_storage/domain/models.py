from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from .value_objects import Path
from .exceptions import DomainError
import uuid
import re

@dataclass
class User:
    login: str
    hashed_password: str
    id_: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self):
        self.validate()

    def validate(self):
        if not self._is_valid_login(self.login):
            raise DomainError("Login must be at least 3 characters long, "
            "with only Latin letters, digits and special character(!@#$%^&*).")

    @staticmethod
    def _is_valid_login(login: str) -> bool:
        pattern = r"^[A-Za-z\d!@#$%^&*]{3,}$"
        return bool(re.fullmatch(pattern, login))



class ResourceType(Enum):
    FILE = "file"
    DIRECTORY = "directory"


@dataclass
class ResourceMetadata:
    path: Path
    type: ResourceType
    size: int | None
    created_at: datetime
    modified_at: datetime
    content_type: str | None = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        if self.type == ResourceType.DIRECTORY and self.size is not None:
            raise DomainError("Directory cannot have size")

        if self.type == ResourceType.FILE and self.size is None:
            raise DomainError("File must have size")

        if self.size is not None and self.size < 0:
            raise DomainError("Resource size cannot be negative")

        if self.type == ResourceType.FILE and not self.content_type:
            raise DomainError("File must have content_type")

        if self.type == ResourceType.DIRECTORY and self.content_type:
            raise DomainError("Directory cannot have content_type")

        if self.created_at > self.modified_at:
            raise DomainError("created_at cannot be after modified_at")

    @property
    def is_file(self) -> bool:
        return self.type == ResourceType.FILE

    @property
    def is_directory(self) -> bool:
        return self.type == ResourceType.DIRECTORY


@dataclass
class DirectoryContent:
    path: Path
    items: list[ResourceMetadata]

    def __post_init__(self):
        self.validate()

    def validate(self):
        for item in self.items:
            if item.path.parent != self.path:
                raise DomainError(
                    f"Item {item.path.value} is not a direct child of {self.path.value}"
                )

        paths = [item.path for item in self.items]
        if len(paths) != len(set(paths)):
            raise DomainError("Directory content contains duplicate paths")

    @property
    def files(self) -> list[ResourceMetadata]:
        return [item for item in self.items if item.is_file]

    @property
    def directories(self) -> list[ResourceMetadata]:
        return [item for item in self.items if item.is_directory]

    @property
    def total_size(self) -> int:
        # не рекурсивно
        return sum(item.size for item in self.files if item.size is not None)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0

    def find_by_name(self, name: str) -> ResourceMetadata | None:
        for item in self.items:
            if item.path.name == name:
                return item
        return None

    def contains(self, name: str) -> bool:
        return self.find_by_name(name) is not None

