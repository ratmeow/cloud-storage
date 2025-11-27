import pytest

from cloud_storage.domain.exceptions import DomainError
from cloud_storage.domain.models import Resource, ResourceType, User
from cloud_storage.domain.value_objects import Path


class TestUser:
    def test_create(self):
        user = User(login="ratmeow", hashed_password="289sdyf87sf")
        assert user.login == "ratmeow"
        assert user.id is not None
        assert user.root_path is not None

    def test_invalid_login(self):
        with pytest.raises(DomainError, match="Login must be"):
            User(login="ba", hashed_password="79df8gd")


class TestPath:
    def test_valid(self):
        path = Path("folder/file.txt")
        assert path.value == "folder/file.txt"

    def test_root(self):
        path = Path("")
        assert path.is_root

    def test_must_not_start_with_slash(self):
        with pytest.raises(DomainError):
            Path("/folder/file.txt")

    def test_cannot_have_double_slash(self):
        with pytest.raises(DomainError):
            Path("folder//file.txt")

    def test_cannot_contain_null_byte(self):
        with pytest.raises(DomainError):
            Path("/folder/\0file.txt")

    def test_parent(self):
        path = Path("folder/subfolder/file.txt")
        assert path.parent == Path("folder/subfolder/")

        path2 = Path("folder")
        assert path2.parent == Path("")

    def test_name(self):
        assert Path("folder/file.txt").name == "file.txt"
        assert Path("folder/").name == "folder"
        assert Path("").name == ""

    def test_is_directory(self):
        path = Path("folder/")
        path_file = Path("folder/test.txt")

        assert path.is_directory
        assert not path_file.is_directory

    def test_join(self):
        path = Path("folder/")
        new_path = path.join("file.txt")

        assert new_path.name == "file.txt"
        assert new_path.parent.name == "folder"

    def test_join_to_file(self):
        with pytest.raises(DomainError):
            Path("folder/file.txt").join("file1.txt")

    def test_relative(self):
        file_path = Path("folder1/folder2/test.txt")

        file_relative_path = file_path.relative_to(Path("folder1/"))
        assert file_relative_path.value == "folder2/test.txt"


class TestResource:
    def test_valid_file(self):
        res = Resource(path=Path("file.txt"), type=ResourceType.FILE, size=1024)
        assert res.name == "file.txt"

    def test_valid_directory(self):
        res = Resource(
            path=Path("folder/"),
            type=ResourceType.DIRECTORY,
            size=None,
        )

        assert res.name == "folder"
