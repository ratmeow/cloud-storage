from dataclasses import dataclass
from .exceptions import DomainError

@dataclass(frozen=True)
class Path:
    value: str

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if self.value.startswith('/'):
            raise DomainError("Path must not start with /")

        invalid_chars = ['\0', '\n', '\r', '\t', "//", "'", '"', ".."]
        for char in invalid_chars:
            if char in self.value:
                raise DomainError(f"Path cannot contain {repr(char)}")

    @property
    def is_root(self) -> bool:
        return self.value == ''

    @property
    def is_directory(self) -> bool:
        return self.value.endswith('/') or self.is_root

    @property
    def parent(self) -> 'Path':
        if self.is_root:
            return self

        parts = self.value.rstrip("/").split("/")

        if len(parts) <= 1:
            return Path('')

        parent = "/".join(parts[:-1]) + "/"
        return Path(parent)

    @property
    def name(self) -> str:
        if self.is_root:
            return ''
        return self.value.rstrip('/').split('/')[-1]

    def join(self, other: 'Path | str') -> 'Path':
        if not self.is_directory:
            raise DomainError("Cannot join to file.")
        if isinstance(other, str):
            other = Path(other)
        if other.is_root:
            return self
        return Path(self.value + other.value)


    def __str__(self) -> str:
        return self.value
