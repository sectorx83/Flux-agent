from pathlib import Path

import pytest

from flux_agent.tools.workspace import Workspace, WorkspaceError


def test_write_and_read_file(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.write_file("src/main.py", "print('hello')\n")
    assert workspace.read_file("src/main.py") == "print('hello')\n"


def test_list_files(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    workspace.write_file("one.txt", "one")
    workspace.write_file("nested/two.txt", "two")
    assert workspace.list_files() == ["nested/", "one.txt"]


def test_reject_path_traversal(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "workspace")
    with pytest.raises(WorkspaceError):
        workspace.resolve("../outside.txt")


def test_reject_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = Workspace(tmp_path / "workspace")
    (workspace.root / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkspaceError):
        workspace.write_file("escape/file.txt", "nope")
