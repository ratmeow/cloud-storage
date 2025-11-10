import pytest
from datetime import datetime
from cloud_storage.domain.models import ResourceMetadata, ResourceType, DirectoryContent, User
from cloud_storage.domain.value_objects import Path, MoveOperation
from cloud_storage.domain.exceptions import DomainError

class TestUser:
    def test_user_create(self):
        user = User(login="ratmeow", hashed_password="289sdyf87sf")
        assert user.login == "ratmeow"
        assert user.id_ is not None

    def test_user_invalid_login(self):
        with pytest.raises(DomainError, match="Login must be"):
            User(login="ba", hashed_password="79df8gd")

class TestPath:
    def test_valid_path(self):
        path = Path("/folder/file.txt")
        assert path.value == "/folder/file.txt"

    def test_root_path(self):
        path = Path("/")
        assert path.value == "/"

    def test_path_must_start_with_slash(self):
        with pytest.raises(DomainError, match="must start with /"):
            Path("folder/file.txt")

    def test_path_cannot_be_empty(self):
        with pytest.raises(DomainError, match="cannot be empty"):
            Path("")

    def test_path_cannot_have_double_slash(self):
        with pytest.raises(DomainError, match="cannot contain double slashes"):
            Path("/folder//file.txt")

    def test_path_cannot_end_with_slash(self):
        with pytest.raises(DomainError, match="cannot end with /"):
            Path("/folder/")

    def test_path_cannot_contain_null_byte(self):
        with pytest.raises(DomainError, match="cannot contain"):
            Path("/folder/\0file.txt")

    def test_path_parent(self):
        path = Path("/folder/subfolder/file.txt")
        assert path.parent == Path("/folder/subfolder")

        path2 = Path("/folder")
        assert path2.parent == Path("/")

    def test_root_has_no_parent(self):
        with pytest.raises(DomainError, match="Root path has no parent"):
            Path("/").parent

    def test_path_name(self):
        assert Path("/folder/file.txt").name == "file.txt"
        assert Path("/folder").name == "folder"
        assert Path("/").name == ""

    def test_path_parts(self):
        path = Path("/folder/subfolder/file.txt")
        assert path.parts == ["folder", "subfolder", "file.txt"]

        assert Path("/").parts == []
        assert Path("/file.txt").parts == ["file.txt"]

    def test_path_depth(self):
        assert Path("/").depth == 0
        assert Path("/folder").depth == 1
        assert Path("/folder/subfolder").depth == 2
        assert Path("/folder/subfolder/file.txt").depth == 3

    def test_path_join(self):
        path = Path("/folder")
        new_path = path.join("file.txt")
        assert new_path == Path("/folder/file.txt")

        root = Path("/")
        new_path2 = root.join("folder")
        assert new_path2 == Path("/folder")

    def test_path_join_rejects_slash(self):
        with pytest.raises(DomainError, match="cannot contain /"):
            Path("/folder").join("sub/file.txt")

    def test_path_join_rejects_empty_name(self):
        with pytest.raises(DomainError, match="cannot be empty"):
            Path("/folder").join("")

    def test_path_join_rejects_dot_names(self):
        with pytest.raises(DomainError, match="cannot be . or .."):
            Path("/folder").join(".")

        with pytest.raises(DomainError, match="cannot be . or .."):
            Path("/folder").join("..")

    def test_is_ancestor_of(self):
        parent = Path("/folder")
        child = Path("/folder/subfolder")
        grandchild = Path("/folder/subfolder/file.txt")

        assert parent.is_ancestor_of(child)
        assert parent.is_ancestor_of(grandchild)
        assert child.is_ancestor_of(grandchild)

        assert not child.is_ancestor_of(parent)
        assert not parent.is_ancestor_of(parent)

    def test_is_descendant_of(self):
        parent = Path("/folder")
        child = Path("/folder/subfolder")

        assert child.is_descendant_of(parent)
        assert not parent.is_descendant_of(child)

    def test_path_equality(self):
        path1 = Path("/folder/file.txt")
        path2 = Path("/folder/file.txt")
        path3 = Path("/folder/other.txt")

        assert path1 == path2
        assert path1 != path3

class TestResourceMetadata:

    def test_valid_file_metadata(self):
        now = datetime.now()
        metadata = ResourceMetadata(
            path=Path("/file.txt"),
            type=ResourceType.FILE,
            size=1024,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        assert metadata.is_file
        assert not metadata.is_directory
        assert metadata.size == 1024

    def test_valid_directory_metadata(self):
        now = datetime.now()
        metadata = ResourceMetadata(
            path=Path("/folder"),
            type=ResourceType.DIRECTORY,
            size=None,
            created_at=now,
            modified_at=now
        )

        assert metadata.is_directory
        assert not metadata.is_file
        assert metadata.size is None

class TestDirectoryContent:

    def test_valid_directory_content(self):
        now = datetime.now()
        parent = Path("/folder")

        item1 = ResourceMetadata(
            path=parent.join("file1.txt"),
            type=ResourceType.FILE,
            size=100,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        item2 = ResourceMetadata(
            path=parent.join("subfolder"),
            type=ResourceType.DIRECTORY,
            size=None,
            created_at=now,
            modified_at=now
        )

        content = DirectoryContent(path=parent, items=[item1, item2])

        assert len(content.items) == 2
        assert len(content.files) == 1
        assert len(content.directories) == 1
        assert not content.is_empty

    def test_empty_directory(self):
        content = DirectoryContent(path=Path("/folder"), items=[])
        assert content.is_empty
        assert len(content.files) == 0
        assert len(content.directories) == 0

    def test_items_must_be_direct_children(self):
        now = datetime.now()
        parent = Path("/folder")

        wrong_item = ResourceMetadata(
            path=Path("/other/file.txt"),
            type=ResourceType.FILE,
            size=100,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        with pytest.raises(DomainError, match="is not a direct child"):
            DirectoryContent(path=parent, items=[wrong_item])

    def test_no_duplicate_paths(self):
        now = datetime.now()
        parent = Path("/folder")

        item1 = ResourceMetadata(
            path=parent.join("file.txt"),
            type=ResourceType.FILE,
            size=100,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        item2 = ResourceMetadata(
            path=parent.join("file.txt"),
            type=ResourceType.FILE,
            size=200,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        with pytest.raises(DomainError, match="duplicate paths"):
            DirectoryContent(path=parent, items=[item1, item2])

    def test_total_size(self):
        now = datetime.now()
        parent = Path("/folder")

        file1 = ResourceMetadata(
            path=parent.join("file1.txt"),
            type=ResourceType.FILE,
            size=100,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        file2 = ResourceMetadata(
            path=parent.join("file2.txt"),
            type=ResourceType.FILE,
            size=200,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        directory = ResourceMetadata(
            path=parent.join("subfolder"),
            type=ResourceType.DIRECTORY,
            size=None,
            created_at=now,
            modified_at=now
        )

        content = DirectoryContent(path=parent, items=[file1, file2, directory])
        assert content.total_size == 300

    def test_find_by_name(self):
        now = datetime.now()
        parent = Path("/folder")

        item = ResourceMetadata(
            path=parent.join("file.txt"),
            type=ResourceType.FILE,
            size=100,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        content = DirectoryContent(path=parent, items=[item])

        found = content.find_by_name("file.txt")
        assert found == item

        not_found = content.find_by_name("other.txt")
        assert not_found is None

    def test_contains(self):
        now = datetime.now()
        parent = Path("/folder")

        item = ResourceMetadata(
            path=parent.join("file.txt"),
            type=ResourceType.FILE,
            size=100,
            created_at=now,
            modified_at=now,
            content_type="text/plain"
        )

        content = DirectoryContent(path=parent, items=[item])

        assert content.contains("file.txt")
        assert not content.contains("other.txt")

class TestMoveOperation:

    def test_cannot_move_to_same_path(self):
        with pytest.raises(DomainError, match="are the same"):
            MoveOperation(
                from_path=Path("/folder/file.txt"),
                to_path=Path("/folder/file.txt")
            )

    def test_cannot_move_into_descendant(self):
        with pytest.raises(DomainError, match="into its own descendant"):
            MoveOperation(
                from_path=Path("/folder"),
                to_path=Path("/folder/subfolder/newname")
            )

    def test_cannot_move_root(self):
        with pytest.raises(DomainError, match="Cannot move root"):
            MoveOperation(
                from_path=Path("/"),
                to_path=Path("/newroot")
            )

    def test_is_rename(self):
        rename = MoveOperation(
            from_path=Path("/folder/oldname.txt"),
            to_path=Path("/folder/newname.txt")
        )
        assert rename.is_rename
        assert not rename.is_move
