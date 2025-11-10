from dataclasses import dataclass
from .exceptions import DomainError

@dataclass(frozen=True)
class Path:
    value: str

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if not self.value:
            raise DomainError("Path cannot be empty")

        if not self.value.startswith('/'):
            raise DomainError("Path must start with /")

        if '//' in self.value:
            raise DomainError("Path cannot contain double slashes")

        if self.value.endswith('/') and self.value != '/':
            raise DomainError("Path cannot end with / except root")

        invalid_chars = ['\0', '\n', '\r', '\t']
        for char in invalid_chars:
            if char in self.value:
                raise DomainError(f"Path cannot contain {repr(char)}")

    @property
    def parent(self) -> 'Path':
        if self.value == '/':
            raise DomainError("Root path has no parent")

        parent_value = '/'.join(self.value.split('/')[:-1])
        return Path(parent_value if parent_value else '/')

    @property
    def name(self) -> str:
        if self.value == '/':
            return ''
        return self.value.split('/')[-1]

    @property
    def parts(self) -> list[str]:
        if self.value == '/':
            return []
        return [p for p in self.value.split('/') if p]

    @property
    def depth(self) -> int:
        return len(self.parts)

    def join(self, name: str) -> 'Path':
        if not name:
            raise DomainError("Name cannot be empty")

        if '/' in name:
            raise DomainError("Name cannot contain /")

        if name in ('.', '..'):
            raise DomainError("Name cannot be . or ..")

        if self.value == '/':
            return Path(f'/{name}')
        return Path(f'{self.value}/{name}')

    def is_ancestor_of(self, other: 'Path') -> bool:
        if self.value == other.value:
            return False
        return other.value.startswith(self.value + '/')

    def is_descendant_of(self, other: 'Path') -> bool:
        return other.is_ancestor_of(self)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if not isinstance(other, Path):
            return False
        return self.value == other.value


@dataclass
class SearchQuery:
    query: str
    root_path: Path | None = None

    def __post_init__(self):
        self.validate()
        self.query = self.query.lower()

    def validate(self):
        if not self.query or not self.query.strip():
            raise DomainError("Search query cannot be empty")

        if len(self.query.strip()) < 2:
            raise DomainError("Search query must be at least 2 characters long")

        if len(self.query) > 255:
            raise DomainError("Search query is too long (max 255 characters)")


@dataclass
class MoveOperation:
    from_path: Path
    to_path: Path

    def __post_init__(self):
        self.validate()

    def validate(self):
        if self.from_path == self.to_path:
            raise DomainError("Source and destination paths are the same")

        if self.to_path.is_descendant_of(self.from_path):
            raise DomainError(
                f"Cannot move {self.from_path.value} into its own descendant {self.to_path.value}"
            )

        if self.from_path.value == '/':
            raise DomainError("Cannot move root directory")

    @property
    def is_rename(self) -> bool:
        try:
            return self.from_path.parent == self.to_path.parent
        except DomainError:
            # Если from_path это корень, parent выбросит ошибку
            return False

    @property
    def is_move(self) -> bool:
        return not self.is_rename